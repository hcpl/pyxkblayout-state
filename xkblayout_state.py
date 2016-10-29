from __future__ import print_function

from xkb import *
from ctypes import *

import sys


class X11Exception(Exception):
    pass


# XKeyboard -----------------------------------------------------------

class XKeyboard():
    def __init__(self):
        self._init_fields()

        self._display = None
        self._group_count = 0
        self._current_group_num = 0
        self._device_id = XkbUseCoreKbd

        XkbIgnoreExtension(False)

        display_name = None
        event_code = c_int()
        error_return = c_int()
        major = c_int(XkbMajorVersion)
        minor = c_int(XkbMinorVersion)
        reason_return = c_int()

        self._display = XkbOpenDisplay(display_name,
            byref(event_code), byref(error_return), byref(major),
            byref(minor), byref(reason_return))

        if reason_return == XkbOD_BadLibraryVersion:
            raise X11Exception("Bad XKB library version.")
        elif reason_return == XkbOD_ConnectionRefused:
            raise X11Exception("Connection to X server refused.")
        elif reason_return == XkbOD_BadServerVersion:
            raise X11Exception("Bad X11 server version.")
        elif reason_return == XkbOD_NonXkbServer:
            raise X11Exception("XKB not present.")
        elif reason_return == XkbOD_Success:
            pass

        if self._initialize_xkb() != True:
            raise X11Exception("XKB not initialized.")

        XkbSelectEventDetails(self._display, XkbUseCoreKbd, XkbStateNotify,
            XkbAllStateComponentsMask, XkbGroupStateMask)

        xkb_state = XkbStateRec()
        XkbGetState(self._display, self._device_id, byref(xkb_state))
        self._current_group_num = (xkb_state.group
            if self._current_group_num != xkb_state.group
            else self._current_group_num)
        self._accomodate_group_xkb()

    def _init_fields(self):
        self._display = None
        self._group_count = 0
        self._group_names = []
        self._symbol_names = []
        self._variant_names = []
        self._current_group_num = 0

        self._device_id = 0
        self._base_event_code = c_int()
        self._base_error_code = c_int()

    def _initialize_xkb(self):
        # Initialize the XKB extension.
        major = c_int(XkbMajorVersion)
        minor = c_int(XkbMinorVersion)
        op_code = c_int()

        # status =
        XkbQueryExtension(self._display,
            byref(op_code), byref(self._base_event_code), byref(self._base_error_code),
            byref(major), byref(minor))

        kbd_desc_ptr = XkbAllocKeyboard()
        if kbd_desc_ptr == None:
            print("Failed to get keyboard description.", file=sys.stderr)
            return False

        kbd_desc_ptr.contents.dpy = self._display
        if self._device_id != XkbUseCoreKbd:
            kbd_desc_ptr.contents.device_spec = self._device_id

        XkbGetControls(self._display, XkbAllControlsMask, kbd_desc_ptr)
        XkbGetNames(self._display, XkbSymbolsNameMask, kbd_desc_ptr)
        XkbGetNames(self._display, XkbGroupNamesMask, kbd_desc_ptr)

        if kbd_desc_ptr.contents.names == None:
            print("Failed to get keyboard description.", file=sys.stderr)
            return False

        # Count the number of configured groups.
        group_source = kbd_desc_ptr.contents.names.contents.groups
        if kbd_desc_ptr.contents.ctrls != None:
            self._group_count = kbd_desc_ptr.contents.ctrls.contents.num_groups
        else:
            self._group_count = 0
            while (self._group_count < XkbNumKbdGroups and
                   group_source[self._group_count] != _None):
                self._group_count += 1

        # There is always at least one group.
        if self._group_count == 0:
            self._group_count = 1

        # Get the group names.
        tmp_group_source = kbd_desc_ptr.contents.names.contents.groups
        cur_group_atom = Atom()
        group_name = ""
        for i in range(self._group_count):
            cur_group_atom = tmp_group_source[i]
            if cur_group_atom != _None:
                group_name_c = XGetAtomName(self._display, cur_group_atom)
                if (group_name_c == None):
                    self._group_names.append("")
                else:
                    group_name = group_name_c.decode()
                    pos = group_name.find('(', 0)
                    if pos != -1:
                        group_name = group_name[:pos-1]
                    self._group_names.append(group_name)
                #XFree(group_name_c)    # Python has GC, munmap_chunk() SIGABRT here

        # Get the symbol name and parse it for layout symbols.
        sym_name_atom = kbd_desc_ptr.contents.names.contents.symbols
        sym_name = ""
        if sym_name_atom != _None:
            sym_name_c = XGetAtomName(self._display, sym_name_atom)
            sym_name = sym_name_c.decode()
            #XFree(sym_name_c)    # Python has GC, munmap_chunk() SIGABRT here
            if (sym_name == ""):
                return False
        else:
            return False

        sym_parser = XkbSymbolParser()
        sym_parser.parse(sym_name, self._symbol_names, self._variant_names)
        count = len(self._symbol_names)
        if count == 1 and self._group_names[0] == "" and self._symbol_names[0] == "jp":
            self._group_count = 2
            self._symbol_names[1] = self._symbol_names[0]
            self._symbol_names[0] = "us"
            self._group_names[0] = "US/ASCII"
            self._group_names[1] = "Japanese"
        else:
            if count < self._group_count:
                k = self._group_count
                for j in reversed(range(count)):
                    k -= 1
                    self._symbol_names[k] = self._symbol_names[j]
                diff = len(self._symbol_names) - k
                if diff < 0:
                    import itertools
                    self._symbol_names.extend(itertools.repeat(None, -diff))
                for k in reversed(range(k)):
                    self._symbol_names[k] = "en_US"

        count = len(self._group_names)
        for i in range(count):
            if self._group_names[i] == "":
                name = self._get_symbol_name_by_res_num(i)
                if name == "":
                    name = "U/A"
                print("Group Name ", i + 1, " is undefined, set to '",
                      name, "'!\n", file=sys.stderr)
                self._group_names[i] = name

        xkb_state = XkbStateRec()
        XkbGetState(self._display, self._device_id, byref(xkb_state))
        self._current_group_num = xkb_state.group

        return True

    def _get_symbol_name_by_res_num(self, group_res_num):
        return self._symbol_names[this._group_num_res_to_xkb(group_res_num)]

    def _get_group_name_by_res_num(self, group_res_num):
        return self._group_names[this._group_num_res_to_xkb(group_res_num)]

    def _group_num_res_to_xkb(self, group_res_num):
        return self._group_lookup(group_res_num, self._group_names, self._symbol_names, self._group_count)

    def _group_lookup(self, src_value, from_text, to_text, count):
        src_text = from_text[src_value]

        if src_text != "":
            for i in range(count):
                target_text = to_text[i]
                if compare_no_case(src_text, target_text) == 0:
                    src_value = i
                    break

        return src_value

    def _accomodate_group_xkb(self):
        state = XkbStateRec()
        XkbGetState(self._display, self._device_id, byref(state))
        self._current_group_num = state.group

    def __del__(self):
        XCloseDisplay(self._display)
        self._display = None

    @property
    def group_count(self):
        return self._group_count

    @property
    def group_names(self):
        return self._group_names

    @property
    def group_symbols(self):
        return self._symbol_names

    @property
    def group_variants(self):
        return self._variant_names

    @property
    def current_group_num(self):
        xkb_state = XkbStateRec()
        XkbGetState(self._display, self._device_id, byref(xkb_state))
        return xkb_state.group

    @property
    def current_group_name(self):
        return self._group_names[self.current_group_num]

    @property
    def current_group_symbol(self):
        return self._symbol_names[self.current_group_num]

    @property
    def current_group_variant(self):
        return self._variant_names[self.current_group_num]

    def set_group_by_num(self, group_num):
        if self._group_count <= 1:
            return False

        result = XkbLockGroup(self._display, self._device_id, group_num)
        if result == False:
            return False
        self._accomodate_group_xkb()
        return True

    def change_group(self, increment):
        result = XkbLockGroup(self._display, self._device_id,
                              (self._current_group_num + increment) % self._group_count)
        if result == False:
            return False
        self._accomodate_group_xkb()
        return True



# XkbSymbolParser -----------------------------------------------------

class XkbSymbolParser():
    def __init__(self):
        self._init_fields()

        self.non_symbols.append("group")
        self.non_symbols.append("inet")
        self.non_symbols.append("pc")

    def __del__(self):
        del self.non_symbols[:]

    def _init_fields(self):
        self.non_symbols = []

    def parse(self, symbols, symbol_list, variant_list):
        in_symbol = False
        cur_symbol = ""
        cur_variant = ""

        #print(symbols)
        # A sample line:
        # pc+fi(dvorak)+fi:2+ru:3+inet(evdev)+group(menu_toggle)

        i = 0
        while i < len(symbols):
            ch = symbols[i]
            if ch == '+' or ch == '_':
                if in_symbol:
                    if self._is_xkb_layout_symbol(cur_symbol):
                        symbol_list.append(cur_symbol)
                        variant_list.append(cur_variant)
                    cur_symbol = ""
                    cur_variant = ""
                else:
                    in_symbol = True
            elif in_symbol and (ch.isalpha() or ch == '_'):
                cur_symbol += ch
            elif in_symbol and ch == '(':
                i += 1
                while (i < len(symbols)):
                    ch = symbols[i]
                    if ch == ')':
                        break
                    else:
                        cur_variant += ch
                    i += 1
            else:
                if in_symbol:
                    if self._is_xkb_layout_symbol(cur_symbol):
                        symbol_list.append(cur_symbol)
                        variant_list.append(cur_variant)
                    cur_symbol = ""
                    cur_variant = ""
                    in_symbol = False
            i += 1

        if in_symbol and cur_symbol != "" and self._is_xkb_layout_symbol(cur_symbol):
            symbol_list.append(cur_symbol)
            variant_list.append(cur_variant)

    def _is_xkb_layout_symbol(self, symbol):
        return not symbol in self.non_symbols


# Helper functions ----------------------------------------------------

if 'cmp' not in globals():
    cmp = lambda x, y: 1 if x > y else 0 if x == y else -1

def normalize_no_case(text):
    return unicodedata.normalize("NFKD", text.casefold())

def compare_no_case(s1, s2):
    return cmp(normalize_no_case(s1), normalize_no_case(s2))

def print_xkeyboard(xkb, file=sys.stdout):
   print("xkb {\n\t", xkb.group_count, " groups {", ", ".join(xkb.group_names),
          "},\n\tsymbols {", ", ".join(xkb.group_symbols), "}\n\tcurrent group: ",
          xkb.current_group_symbol, " - ", xkb.current_group_name,
          " (", xkb.current_group_num, ")\n}", sep="", end="\n", file=file)

# Main entry point (test) ---------------------------------------------

def main():
    xkb = XKeyboard()
    print_xkeyboard(xkb)
    xkb.change_group(1)
    print_xkeyboard(xkb)
    xkb.change_group(1)
    print_xkeyboard(xkb)
    xkb.change_group(1)
    print_xkeyboard(xkb)

if __name__ == '__main__':
    main()
