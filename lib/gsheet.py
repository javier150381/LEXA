import os
from typing import Optional

try:
    import gspread
except Exception:  # noqa: BLE001 - optional dependency may not be installed
    gspread = None


def get_sheet() -> Optional[object]:
    """Return the configured Google Sheet worksheet or ``None`` if unavailable."""
    cred_path = os.getenv("AV_SHEETS_CREDENTIALS")
    sheet_id = os.getenv("AV_SHEETS_ID")
    if not gspread or not cred_path or not sheet_id:
        return None
    try:
        gc = gspread.service_account(filename=cred_path)
        sh = gc.open_by_key(sheet_id)
        sheet_name = os.getenv("AV_SHEETS_NAME")
        return sh.worksheet(sheet_name) if sheet_name else sh.sheet1
    except Exception:
        return None


def sheet_has_code(sheet: object | None, code: str) -> bool:
    """Return ``True`` if ``code`` is found in ``sheet``."""
    if sheet is None:
        return False
    try:
        return sheet.find(code) is not None
    except Exception:
        return False


def sheet_add_code(sheet: object | None, code: str) -> None:
    """Append ``code`` to ``sheet``."""
    if sheet is None:
        return
    try:
        sheet.append_row([code])
    except Exception:
        pass
