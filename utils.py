def number_to_words(num):
    """Convert a number to words representation"""
    units = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def _convert_less_than_thousand(num):
        if num < 20:
            return units[num]
        elif num < 100:
            return tens[num // 10] + ('' if num % 10 == 0 else ' ' + units[num % 10])
        else:
            return units[num // 100] + ' Hundred' + ('' if num % 100 == 0 else ' and ' + _convert_less_than_thousand(num % 100))

    if num == 0:
        return 'Rupees Zero Only'

    # Handle decimal part
    rupees = int(num)
    paise = int(round((num - rupees) * 100))

    result = 'Rupees '
    crore = rupees // 10000000
    rupees %= 10000000
    lakh = rupees // 100000
    rupees %= 100000
    thousand = rupees // 1000
    rupees %= 1000

    if crore:
        result += _convert_less_than_thousand(crore) + ' Crore '
    if lakh:
        result += _convert_less_than_thousand(lakh) + ' Lakh '
    if thousand:
        result += _convert_less_than_thousand(thousand) + ' Thousand '
    if rupees:
        result += _convert_less_than_thousand(rupees)

    if paise:
        result += ' and ' + _convert_less_than_thousand(paise) + ' Paise'

    return result.strip() + ' Only'

def calculate_business_days(start_date, end_date):
    """
    Calculate the number of business days (excluding weekends) between two dates.

    Args:
        start_date (datetime): The start date
        end_date (datetime): The end date

    Returns:
        int: The number of business days between the two dates, with same-day counting as 1
    """
    if not start_date or not end_date:
        return 0

    # Ensure we're working with datetime objects
    if isinstance(start_date, str):
        from datetime import datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
    if isinstance(end_date, str):
        from datetime import datetime
        end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')

    # If end_date is before start_date, return 0
    if end_date < start_date:
        return 0

    # Convert to date objects (removing time component)
    from datetime import datetime, timedelta
    start_date_only = start_date.date()
    end_date_only = end_date.date()

    # If same day, return 1
    if start_date_only == end_date_only:
        return 1

    # Calculate the number of days between the two dates
    days = (end_date_only - start_date_only).days

    # Add 1 to count the start day (since same-day should be 1)
    calendar_days = days + 1

    # Count business days by iterating through each day
    business_days = 0
    current_date = start_date_only

    for _ in range(calendar_days):
        # Check if current day is a weekday (0-4 are Monday to Friday)
        if current_date.weekday() < 5:
            business_days += 1

        # Move to next day
        current_date += timedelta(days=1)

    return business_days

def calculate_processing_days(epv, finance_entry):
    """
    Calculate the processing days for an EPV based on its status:
    - For regular EPVs: Date of payment - Date of manager approval (excluding weekends)
    - For resubmitted EPVs: Date of resubmission - Date of payment (excluding weekends)

    Args:
        epv (EPV): The EPV record
        finance_entry (FinanceEntry): The finance entry record

    Returns:
        int: The number of business days for processing
    """
    from datetime import datetime
    from models import EPVApproval

    # If we don't have a finance entry with payment date, return 0
    if not finance_entry or not finance_entry.payment_date:
        return 0

    # Check if this is a resubmitted EPV
    is_resubmitted = False
    resubmission_date = None

    # Find the resubmission record (system approval with status='resubmitted')
    resubmission = EPVApproval.query.filter_by(
        epv_id=epv.id,
        status='resubmitted',
        approver_email='system@webapporbit.com'
    ).order_by(EPVApproval.action_date.desc()).first()

    if resubmission and resubmission.action_date:
        is_resubmitted = True
        resubmission_date = resubmission.action_date

    # For resubmitted EPVs: Date of resubmission - Date of payment
    if is_resubmitted and resubmission_date:
        # Calculate business days between resubmission date and payment date
        return calculate_business_days(resubmission_date, finance_entry.payment_date)

    # For regular EPVs: Date of payment - Date of manager approval
    else:
        # Find the manager approval date (when status changed to 'approved')
        manager_approval = EPVApproval.query.filter_by(
            epv_id=epv.id,
            status='approved'
        ).order_by(EPVApproval.action_date).first()

        # If we have both dates, calculate business days between them
        if manager_approval and manager_approval.action_date:
            return calculate_business_days(manager_approval.action_date, finance_entry.payment_date)

    # Default return if we can't calculate
    return 0
