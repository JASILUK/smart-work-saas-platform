import datetime
from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import EmployeeShiftAssignment, Shift
from apps.attendance.selectors.employee_shift_assignment_selectors import EmployeeShiftAssignmentSelector


class EmployeeShiftAssignmentService:
    """
    Orchestration service handling write operations, lifecycle state transitions, 
    and date-effective business rules for employee shift assignments.
    """

    # =====================================================
    # ASSIGN SHIFT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def assign_shift(
        *,
        membership: Any,
        shift: Shift,
        effective_from: datetime.date,
        effective_until: Optional[datetime.date] = None,
        assigned_by: Any,
        notes: str = "",
    ) -> EmployeeShiftAssignment:
        """
        Creates a new date-effective shift assignment for an employee.
        Validates tenant isolation rules and checks for schedule timeline conflicts.
        """
        # 1. Enforce company consistency between the membership and the target shift
        if membership.company_id != shift.company_id:
            raise ValidationError("Membership and Shift must belong to the same company.")

        # 2. Validate chronological order of the provided date range
        if effective_until is not None and effective_until < effective_from:
            raise ValidationError("The assignment end date cannot be earlier than the start date.")

        # 3. Prevent duplicate or overlapping assignments for the same date range
        if EmployeeShiftAssignmentSelector.has_overlapping_assignment(
            membership=membership,
            effective_from=effective_from,
            effective_until=effective_until,
        ):
            raise ValidationError("This employee already has a shift assignment during this period.")

        # 4. Initialize and persist the assignment record in the database
        assignment = EmployeeShiftAssignment.objects.create(
            membership=membership,
            shift=shift,
            effective_from=effective_from,
            effective_until=effective_until,
            assigned_by=assigned_by,
            notes=str(notes).strip(),
            is_active=True,
        )
        return assignment

    # =====================================================
    # UPDATE ASSIGNMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update_assignment(
        *,
        assignment: EmployeeShiftAssignment,
        validated_data: Dict[str, Any],
    ) -> EmployeeShiftAssignment:
        """
        Updates an existing shift assignment record. 
        Re-validates date constraints and checks for schedule overlaps while protecting historical data.
        """
        # 4. Block accidental or structural modifications to the membership record link
        if "membership" in validated_data and validated_data["membership"] != assignment.membership:
            raise ValidationError("Changing the employee link on an existing assignment is not allowed.")

        # Resolve field values by checking the incoming patch against current instance properties
        shift = validated_data.get("shift", assignment.shift)
        effective_from = validated_data.get("effective_from", assignment.effective_from)
        effective_until = validated_data.get("effective_until", assignment.effective_until)

        # 1. Validate chronological order of the updated date range
        if effective_until is not None and effective_until < effective_from:
            raise ValidationError("The assignment end date cannot be earlier than the start date.")

        # Re-verify tenant boundary alignment if a new shift target is provided
        if shift.company_id != assignment.membership.company_id:
            raise ValidationError("The selected Shift must belong to the same company as the employee.")

        # 2. Check for overlaps while excluding the current assignment record from the query check
        if EmployeeShiftAssignmentSelector.has_overlapping_assignment(
            membership=assignment.membership,
            effective_from=effective_from,
            effective_until=effective_until,
            exclude_id=assignment.id,
        ):
            raise ValidationError("This employee already has a shift assignment during this period.")

        # 5. Apply modifications dynamically and save changed fields only
        update_fields = []
        
        # 3. Process field modifications for authorized, editable fields
        allowed_fields = ["shift", "effective_from", "effective_until", "notes"]
        for field in allowed_fields:
            if field in validated_data:
                value = validated_data[field]
                if field == "notes":
                    value = str(value).strip()
                setattr(assignment, field, value)
                update_fields.append(field)

        if update_fields:
            if hasattr(assignment, "modified"):
                update_fields.append("modified")
            assignment.save(update_fields=update_fields)

        return assignment

    # =====================================================
    # END ASSIGNMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def end_assignment(
        *,
        assignment: EmployeeShiftAssignment,
        end_date: datetime.date,
    ) -> EmployeeShiftAssignment:
        """
        Closes an active shift assignment timeline by applying a definitive end date.
        """
        # 1. Enforce that the end date cannot be set before the timeline's start date
        if end_date < assignment.effective_from:
            raise ValidationError("The termination end date cannot be earlier than the assignment start date.")

        assignment.effective_until = end_date
        update_fields = ["effective_until"]

        # 3. Automatically mark the assignment inactive if the end date falls in a past cycle
        today = timezone.localdate()
        if end_date < today:
            assignment.is_active = False
            update_fields.append("is_active")

        if hasattr(assignment, "modified"):
            update_fields.append("modified")

        # 4. Save updates to the database
        assignment.save(update_fields=update_fields)
        return assignment

    # =====================================================
    # DEACTIVATE ASSIGNMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def deactivate_assignment(
        *,
        assignment: EmployeeShiftAssignment,
    ) -> EmployeeShiftAssignment:
        """
        Immediately deactivates an assignment timeline and sets its end date to today.
        """
        # 1. Return immediately if the target instance is already marked inactive
        if not assignment.is_active:
            return assignment

        today = timezone.localdate()
        
        # 2. Update status attributes to truncate the active window today
        assignment.is_active = False
        assignment.effective_until = today
        update_fields = ["is_active", "effective_until"]

        if hasattr(assignment, "modified"):
            update_fields.append("modified")

        # 3. Save updates to the database
        assignment.save(update_fields=update_fields)
        return assignment

    # =====================================================
    # BULK ASSIGN SHIFT
    # =====================================================

    @staticmethod
    def bulk_assign_shift(
        *,
        memberships: List[Any],
        shift: Shift,
        effective_from: datetime.date,
        effective_until: Optional[datetime.date] = None,
        assigned_by: Any,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Assigns a uniform shift template across a list of employees.
        Isolates individual row validation failures to ensure valid records are processed successfully.
        """
        summary = {
            "total": len(memberships),
            "created": 0,
            "skipped": 0,
            "errors": [],
        }

        # 1. Pre-flight check: Verify that the end date cannot be set before the start date
        if effective_until is not None and effective_until < effective_from:
            raise ValidationError("The assignment end date cannot be earlier than the start date.")

        cleaned_notes = str(notes).strip()

        for emp in memberships:
            # 1. Enforce company tenant boundary matching controls per iteration row
            if emp.company_id != shift.company_id:
                summary["skipped"] += 1
                summary["errors"].append({
                    "membership_id": emp.id,
                    "error": "The selected shift belongs to a different company workspace.",
                })
                continue

            # 2. Catch and skip records that have conflicting schedule overlaps
            if EmployeeShiftAssignmentSelector.has_overlapping_assignment(
                membership=emp,
                effective_from=effective_from,
                effective_until=effective_until,
            ):
                summary["skipped"] += 1
                summary["errors"].append({
                    "membership_id": emp.id,
                    "error": "This employee already has a shift assignment during this period.",
                })
                continue

            try:
                # 3. Wrap individual row mutations in isolated atomic contexts to prevent batch rollback cascades
                with transaction.atomic():
                    EmployeeShiftAssignment.objects.create(
                        membership=emp,
                        shift=shift,
                        effective_from=effective_from,
                        effective_until=effective_until,
                        assigned_by=assigned_by,
                        notes=cleaned_notes,
                        is_active=True,
                    )
                summary["created"] += 1
            except Exception as exc:
                # 4. Safely log unforeseen persistence errors without interrupting the main loop
                summary["skipped"] += 1
                summary["errors"].append({
                    "membership_id": emp.id,
                    "error": f"Database operation aborted: {str(exc)}",
                })

        return summary

    # =====================================================
    # TRANSFER SHIFT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def transfer_shift(
        *,
        assignment: EmployeeShiftAssignment,
        new_shift: Shift,
        effective_from: datetime.date,
        assigned_by: Any,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Transfers an employee to a new shift rotation line.
        Atomically ends the previous assignment to maintain a clean, unbroken history timeline.
        """
        membership = assignment.membership

        # 1. Enforce tenant boundary matching rules for the proposed shift profile
        if new_shift.company_id != membership.company_id:
            raise ValidationError("The new shift assignment must belong to the same company.")

        # Enforce that a transfer cannot take effect before the current assignment's original start date
        if effective_from <= assignment.effective_from:
            raise ValidationError("The shift transfer effective date must be later than the current assignment's start date.")

        # 2. Close out the previous assignment exactly one day before the transfer takes effect
        previous_end_date = effective_from - datetime.timedelta(days=1)
        
        # Modify and update fields on the existing row directly
        assignment.effective_until = previous_end_date
        update_fields = ["effective_until"]

        today = timezone.localdate()
        if previous_end_date < today:
            assignment.is_active = False
            update_fields.append("is_active")

        if hasattr(assignment, "modified"):
            update_fields.append("modified")
        assignment.save(update_fields=update_fields)

        # 3. Create the new consecutive assignment timeline row
        # 4. Overlap checks run dynamically through the underlying create sequence to protect historical integrity
        new_assignment = EmployeeShiftAssignment.objects.create(
            membership=membership,
            shift=new_shift,
            effective_from=effective_from,
            effective_until=None,  # Set open-ended until a future rotation change occurs
            assigned_by=assigned_by,
            notes=str(notes).strip(),
            is_active=True,
        )

        # 5. Return references for both historical tracking segments
        return {
            "previous_assignment": assignment,
            "new_assignment": new_assignment,
        }