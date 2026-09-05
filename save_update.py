import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


VERSION_FILE = Path(__file__).with_name("version_history.json")
README_FILE = Path(__file__).with_name("README.md")
README_START = "<!-- VERSION_HISTORY_START -->"
README_END = "<!-- VERSION_HISTORY_END -->"
THAILAND_TIMEZONE = timezone(timedelta(hours=7), name="Asia/Bangkok")


def split_items(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def make_summary(systems: list[str], duties: list[str], note: str) -> str:
    system_text = ", ".join(systems)
    duty_text = ", ".join(duties)
    return f"อัปเดต {system_text} โดยเพิ่มหน้าที่: {duty_text} หมายเหตุ: {note}"


def update_readme(history: dict) -> None:
    releases = history.get("releases", [])
    lines = [
        "## ประวัติการอัปเดต",
        "",
        "สรุปการเปลี่ยนแปลงของระบบในแต่ละเวอร์ชัน",
        "",
    ]
    for release in releases:
        lines.extend(
            [
                f"### เวอร์ชัน {release.get('version', '-')}",
                f"- วันที่: `{release.get('released_at', '-')}`",
                f"- สรุป: {release.get('summary', release.get('note', '-'))}",
                "- ระบบที่เพิ่ม/แก้ไข:",
                *[f"  - {item}" for item in release.get("systems", [])],
                "- หน้าที่ของระบบ:",
                *[f"  - {item}" for item in release.get("duties", [])],
                "",
            ]
        )
    section = f"{README_START}\n" + "\n".join(lines).rstrip() + f"\n{README_END}"
    existing = README_FILE.read_text(encoding="utf-8") if README_FILE.exists() else "# Bot\n"
    if README_START in existing and README_END in existing:
        start = existing.index(README_START)
        end = existing.index(README_END, start) + len(README_END)
        content = existing[:start] + section + existing[end:]
    else:
        content = existing.rstrip() + "\n\n" + section + "\n"
    README_FILE.write_text(content, encoding="utf-8")


def save_update(version: str, systems: list[str], duties: list[str], note: str) -> None:
    with VERSION_FILE.open(encoding="utf-8") as file:
        history = json.load(file)

    summary = make_summary(systems, duties, note)
    release = {
        "version": version,
        "systems": systems,
        "duties": duties,
        "note": note,
        "summary": summary,
        "released_at": datetime.now(THAILAND_TIMEZONE).isoformat(timespec="seconds"),
        "timezone": "Asia/Bangkok",
    }
    releases = history.setdefault("releases", [])
    releases[:] = [item for item in releases if item.get("version") != version]
    releases.insert(0, release)
    history["current_version"] = version
    update_readme(history)

    with VERSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"บันทึกประวัติเวอร์ชัน {version} เรียบร้อยแล้ว")
    print(f"วันเวลา: {release['released_at']}")
    print(f"บทสรุป: {summary}")


def interactive_save() -> tuple[str, list[str], list[str], str]:
    version = input("เวอร์ชัน: ").strip()
    systems = split_items(input("ระบบที่เพิ่ม (คั่นด้วย ,): "))
    duties = split_items(input("หน้าที่ของระบบ (คั่นด้วย ,): "))
    note = input("หมายเหตุเพิ่มเติม: ").strip()

    if not version or not systems or not duties or not note:
        raise ValueError("กรุณากรอกเวอร์ชัน ระบบที่เพิ่ม หน้าที่ และหมายเหตุให้ครบ")
    return version, systems, duties, note


def main() -> None:
    parser = argparse.ArgumentParser(description="บันทึกประวัติการอัปเดตระบบ")
    parser.add_argument("command", help="ใช้ Save เพื่อบันทึกการอัปเดต")
    parser.add_argument("--version", help="เลขเวอร์ชันใหม่")
    parser.add_argument("--systems", help="รายการระบบที่เพิ่ม คั่นด้วย comma")
    parser.add_argument("--duties", help="รายการหน้าที่ คั่นด้วย comma")
    parser.add_argument("--note", help="หมายเหตุเพิ่มเติมของการอัปเดต")
    args = parser.parse_args()

    if args.command.lower() != "save":
        parser.error("คำสั่งต้องเป็น Save")

    if any(value is None for value in (args.version, args.systems, args.duties, args.note)):
        version, systems, duties, note = interactive_save()
    else:
        version = args.version.strip()
        systems = split_items(args.systems)
        duties = split_items(args.duties)
        note = args.note.strip()
        if not version or not systems or not duties or not note:
            parser.error("version, systems, duties และ note ต้องไม่ว่าง")

    save_update(version, systems, duties, note)


if __name__ == "__main__":
    main()
