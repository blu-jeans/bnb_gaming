## 2026-07-13T16:30:11+08:00
Your identity is teamwork_preview_worker.
Your working directory is d:\workspace\bnb_guessing\.agents\worker_db_update.

Objective:
Update the database schema, models, and initialization logic to support the new requirement for pre-populated family members and the banker role.

Requirements:
1. Update `src/database/models.py`:
   - Add `is_banker: bool = False` to the `Member` dataclass.
2. Update `src/database/repository.py`:
   - Modify the `members` table creation SQL to include `is_banker INTEGER NOT NULL DEFAULT 0`.
   - Update `initialize_db()` to check if the `members` table is empty. If it is, pre-populate it with the 34 family members:
     棉花, P5, 斌, 滋味, F, 冰, 雀占, 小黑, 仁俊, 大宝, 爱恋, 恋, 蟋蟀, 君王, 月子, 老王, 螺丝, 千序, 兰兰, 燕子, 咬字, 欢, 娜娜, 托尼, 敏宝, 通, 飓风, 爱火花, 今天, 李硕, 觅魅, 车, 主持人, 大哥.
   - Flag `"主持人"` with `is_banker = 1` (True) in the database, and all other members as `is_banker = 0` (False).
   - Update `add_member` to accept `is_banker: bool = False` and insert it into the database.
   - Update SQL selects and Member object instantiation to handle the `is_banker` field.
3. Update `tests/test_helper.py`:
   - Modify the `members` table creation SQL to include `is_banker INTEGER DEFAULT 0`.
   - Update the default members pre-population logic to populate the same 34 family members, with `"主持人"` flagged as banker (`is_banker = 1`).
   - If there are other places referencing member creation or queries in `tests/test_helper.py`, update them to be compatible with the new field.

Scope boundaries:
- ONLY make changes to `src/database/models.py`, `src/database/repository.py`, and `tests/test_helper.py`.
- Strictly adhere to Key Constraints:
  - DO NOT run any terminal commands for testing, launching, or packaging (ABSOLUTE BAN on: python, pytest, pyinstaller, running apps, launching .py files).
  - ONLY write complete, working code files using replace_file_content or write_to_file.
  - Keep all code comments and documentation in Simplified Chinese (简体中文).
  - Use fixed author @author hyq.

Output requirements:
- Write a report (handoff.md) in your working directory listing the exact changes made to each file.

Completion criteria:
- Database schema and models support the `is_banker` flag.
- The 34 members are pre-populated on first launch with `"主持人"` set as banker.
- `tests/test_helper.py` is fully aligned with these database changes.
- Handoff report is written.
