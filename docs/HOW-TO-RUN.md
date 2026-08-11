# How to Run — Payment File Generator (for payroll staff)

This tool turns the monthly **Deduction list** spreadsheet into the **payment file**
you upload to Westpac **Business Online**. No typing, no programming.

You do the one-time setup **once**. After that it's: drop the file in, double-click, done.

---

## Windows (most users)

### One-time setup (do this once)

1. Go to **https://www.python.org/downloads/** and click the big **Download Python**
   button.
2. Open the downloaded file. On the **first installer screen**, **tick the box that says
   "Add python.exe to PATH"** (bottom of the window). This step matters — don't skip it.
3. Click **Install Now**, wait for it to finish, then click **Close**.

You only ever do this once on your computer.

### Every month

1. Save this month's spreadsheet into the **`input`** folder (inside this tool's folder).
   The file must end in **`.xlsx`**. Keep only the current month's file in there.
2. Double-click **`run.bat`**.
3. A black window opens and runs the tool:
   - If it worked, you'll see **`OK: wrote 5 payment(s), total $...`**.
   - The window stays open so you can read it. Close it when done.
4. Open the **`output`** folder. Your payment file is there, named like
   **`deskbank_payment_280826_20260828-131500.csv`** — the first number is the payment
   date (DDMMYY) and the rest is the date/time it was generated, so each run makes a new
   file and never overwrites a previous one.
5. Upload that `.csv` file into Business Online as a Deskbank import.

---

## Mac

### One-time setup

1. Go to **https://www.python.org/downloads/** and download Python for macOS.
2. Open the downloaded `.pkg` file and click through **Continue → Install**.

### Every month

1. Put this month's `.xlsx` into the **`input`** folder.
2. Double-click **`run.command`**.
   - **First time only:** if Mac says it "cannot be opened", **right-click** the file →
     **Open** → **Open**. After that, a normal double-click works.
3. Read the result in the window, then find your file in the **`output`** folder.
4. Upload that `.csv` to Business Online.

---

## If something looks wrong

The tool checks the spreadsheet before making the file. If a value is bad, it **stops and
writes no file**, and prints one clear line telling you exactly what and where. Examples:

```
ERROR: Row 6 (KELROS045): Amount 'twenty' is not a number -> enter a positive dollar value, e.g. 35 or 35.00
ERROR: Row 4: Bank Details '98-7654-234567' has 3 part(s), expected Bank-Branch-Account-Suffix -> e.g. 98-7654-1234567-001
ERROR: Deduction list: 'From account' not found -> add it as e.g. 12-3456-7654321 in the cell to its right
```

**What to do:** open the spreadsheet in the `input` folder, fix the row/value it names,
save, and double-click the launcher again.

You may also see **`WARNING:`** lines (e.g. a name longer than 20 characters is shortened).
Warnings do **not** stop the file — they just tell you what was adjusted. Check they're OK.

### Things to avoid in the spreadsheet
- **No commas** and **no quote marks** in text cells (Beneficiary, Particulars, Code,
  Reference). The bank rejects them.
- Amounts are **dollars** (e.g. `35` or `35.50`) — the tool converts them to the bank's
  cents format automatically.

---

## What the tool does (in one line)
Reads `Date of Payment`, `From account`, and each beneficiary row from the spreadsheet,
and writes a Westpac **Deskbank CSV** file (one header + one payment per row) ready to
upload to Business Online.
