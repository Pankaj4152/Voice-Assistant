# ... (keep the beginning of the function the same: finding notepad_window)

# Debug tree (you already have this)
print("\nUIA Tree under Notepad window:")
print_uia_tree(notepad_window)

# Step 3: Find the DocumentControl (main rich text area in modern Notepad)
document = notepad_window.DocumentControl(searchDepth=3)  # should be close to top

if document.Exists(0):
    print("DocumentControl found! (this is the text editor area in Windows 11+ Notepad)")
    
    # Modern Notepad's text is usually exposed via ValuePattern or TextPattern
    try:
        # Option A: ValuePattern (often works for simple/rich edit)
        value_pattern = document.GetValuePattern()
        if value_pattern:
            full_text = value_pattern.Value
            print("Read via ValuePattern")
            return full_text
    except Exception as e:
        print(f"ValuePattern not supported: {e}")

    # Option B: TextPattern (better for rich/multi-line documents)
    try:
        text_pattern = document.GetTextPattern()  # or document.GetCurrentPattern(TextPattern.Pattern)
        if text_pattern:
            # Get full document range and its text
            document_range = text_pattern.DocumentRange
            full_text = document_range.GetText(-1)  # -1 = get all text
            print("Read via TextPattern")
            return full_text
    except Exception as e:
        print(f"TextPattern failed: {e}")

    # Option C: Fallback to legacy accessible value (if patterns missing)
    try:
        legacy = document.GetLegacyIAccessiblePattern()
        if legacy and legacy.Value:
            print("Read via LegacyIAccessible")
            return legacy.Value
    except:
        pass

    # Last resort: Name sometimes has partial info (unlikely full text)
    return document.Name or ""

else:
    print("DocumentControl not found.")

# Step 4: Keep your Win32 fallback (it should work great now that we have the window)
# ... (your existing get_text_via_win32() function)

# In the fallback, you can even improve enum to look for 'RichEditD2DPT'
def get_text_via_win32():
    hwnd = notepad_window.NativeWindowHandle
    def enum_child(hwnd_child, results):
        class_name = win32gui.GetClassName(hwnd_child)
        if class_name in ['Edit', 'RichEditD2DPT', 'RichEdit50W']:  # cover all variants
            results.append(hwnd_child)
        return True

    results = []
    win32gui.EnumChildWindows(hwnd, enum_child, results)
    if not results:
        print("No suitable edit/rich edit child window found")
        return None
    
    edit_hwnd = results[0]  # take first match
    length = win32gui.SendMessage(edit_hwnd, win32con.WM_GETTEXTLENGTH, 0, 0) + 1
    if length <= 1:
        return ""  # empty
    
    buffer = win32gui.PyMakeBuffer(length)
    win32gui.SendMessage(edit_hwnd, win32con.WM_GETTEXT, length, buffer)
    text = buffer.value.decode('utf-8', errors='replace').rstrip('\x00')
    print("Read successfully via Win32 (WM_GETTEXT)")
    return text