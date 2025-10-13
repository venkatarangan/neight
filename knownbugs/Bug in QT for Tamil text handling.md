# Tamil Text Navigation Issue – QT Treats Certain Consonant+Pulli+Consonant Sequences as Single Grapheme Clusters (Should Be Separate)

### Summary

When editing Tamil text in Qt widgets such as `QTextEdit`, `QPlainTextEdit`, or `QLineEdit`, cursor navigation and text selection behave incorrectly for certain letter combinations.

Qt currently treats some **consonant + pulli (virama) + consonant** sequences as a single grapheme cluster.
In Tamil, however, these should be treated as **two separate logical letters**.

As a result, when using the **Left Arrow** or **Right Arrow** keys, the cursor jumps over an entire combination instead of moving through each character.

---

### Affected Versions

* Qt Runtime 6.10.0 on Windows 11

### Steps to Reproduce

1. Create a minimal test application with a text edit widget:

   ```python
   from PySide6.QtWidgets import QApplication, QTextEdit

   app = QApplication([])
   text = QTextEdit()
   text.setPlainText("ற்க ண்டு ல்லா த்த ங்க ப்பி")
   text.show()
   app.exec()
   ```

2. Type or paste the following Tamil text into the editor:

   ```
   ர்க  ண்டு  ல்லா  த்த  ங்க  ப்பி
   ```

3. Use the **Left Arrow** and **Right Arrow** keys to navigate through the text.

4. Observe how the cursor skips over combinations like “ர்க” or “ண்டு” as single units instead of moving between their parts.

---

### Expected Behaviour

Each combination should allow cursor movement between the constituent characters.

| Displayed Form | Should be Treated As | Unicode Codepoints           |
| -------------- | -------------------- | ---------------------------- |
| ர்க            | ர், க                | U+0BB0 U+0BCD, U+0B95        |
| ண்டு           | ண், டு               | U+0BA3 U+0BCD, U+0B9F U+0BC1 |
| ல்லா           | ல், லா               | U+0BB2 U+0BCD, U+0BB2 U+0BBE |
| த்த            | த், த                | U+0BA4 U+0BCD, U+0BA4        |
| ங்க            | ங், க                | U+0B99 U+0BCD, U+0B95        |
| ப்பி           | ப், பி               | U+0BAA U+0BCD, U+0BAA U+0BBF |

Cursor navigation should move **from “ர்” to “க”**, not skip both together.

---

### Actual Behaviour (Current Qt)

Qt treats these combinations as **single grapheme clusters**.
You cannot place the cursor between “ர்” and “க” or “ங்” and “க”.

This makes Tamil text editing unintuitive, especially when using keyboard navigation or backspace/delete operations.

---

### Root Cause

Tamil uses the **virama (pulli)** character `U+0BCD` to suppress the inherent vowel sound of a consonant.
When a consonant + pulli is followed by another consonant, Qt’s text shaping engine (via HarfBuzz) incorrectly groups them into one grapheme cluster.

In Tamil orthography:

* “க் + க” is *not* a conjunct ligature; it represents **two distinct letters**.
* The visual rendering remains separate, unlike Devanagari where consonant clusters form conjuncts.

Thus, Qt’s current segmentation is linguistically inaccurate for Tamil.

---

### Technical Notes

* Tamil’s virama (்) does not create conjunct ligatures.
* Unicode allows **language-specific tailoring** for grapheme cluster segmentation.
* In Tamil, segmentation should stop after a pulli (`U+0BCD`).

**References:**

* Unicode Standard Annex #29: [Unicode Text Segmentation](https://unicode.org/reports/tr29/)
* Unicode Tamil Block Chart: [https://www.unicode.org/charts/PDF/U0B80.pdf](https://www.unicode.org/charts/PDF/U0B80.pdf)
* Unicode Technical Note #31: [Tamil Script Notes](https://www.unicode.org/notes/tn31/)
* HarfBuzz Clustering Docs: [https://harfbuzz.github.io/](https://harfbuzz.github.io/)

---

**Long-term fix (for Qt maintainers):**
Adjust Tamil-specific grapheme segmentation:

* Treat *consonant + pulli + consonant* as **two clusters**
* Continue treating *consonant + pulli + vowel sign* as a **single cluster** (current behaviour is correct)

This change would bring Tamil behaviour in line with text editors and apps like:

* Windows Notepad
* Microsoft Word
* Google Chrome
* Microsoft Edge
* Firefox 
—all of which correctly navigate through Tamil characters individually.

---
### Why It Matters

This issue affects all Tamil text editing in Qt-based applications, including Notepad-like apps, IDEs, and translation tools. Tamil users experience inconsistent and unintuitive cursor navigation compared to native platform editors.

Fixing this will significantly improve Tamil input handling across Qt applications and enhance accessibility for millions of Tamil speakers.

---

### References

1. Unicode Tamil block chart – [https://www.unicode.org/charts/PDF/U0B80.pdf](https://www.unicode.org/charts/PDF/U0B80.pdf)
2. Unicode Text Segmentation (UAX #29) – [https://unicode.org/reports/tr29/](https://unicode.org/reports/tr29/)
3. Tamil script notes from Unicode – [https://unicode.org/notes/tn31/](https://unicode.org/notes/tn31/)
4. HarfBuzz grapheme clustering logic – [https://harfbuzz.github.io/](https://harfbuzz.github.io/)
