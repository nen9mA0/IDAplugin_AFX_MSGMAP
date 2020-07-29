﻿# pylint: disable=C0301,C0103

# ==============================================================================
# AfxMSGMap plugin for IDA
# Copyright (c) 2018
# Snow 85703533
# Port to IDA 7x by HTC - VinCSS (a member of Vingroup)
# All rights reserved.
#
# ==============================================================================

import idautils
import idaapi
import idc
import ida_segment
import ida_struct
import ida_nalt
import ida_typeinf
import ida_moves

plugin_initialized = False


def set_bookmark(addr, description):
    """ Add bookmark with description at addr """
    for slot in range(ida_moves.MAX_MARK_SLOT):
        ea = idc.get_bookmark(slot)
        if ea == idc.BADADDR:
            idc.put_bookmark(addr, 0, 0, 0, slot, description)
            return


class AFXMSGMAPSearchResultChooser(idaapi.Choose):
    def __init__(self, title, items, flags=0, width=None, height=None, embedded=False):
        idaapi.Choose.__init__(self,
                               title,
                               [["Index", idaapi.Choose.CHCOL_PLAIN|6],
                                ["Address", idaapi.Choose.CHCOL_HEX|20],
                                ["Name", idaapi.Choose.CHCOL_HEX|40],
                                ["Entry Num", idaapi.Choose.CHCOL_HEX|10],],
            flags=flags,
            width=width,
            height=height,
            embedded=embedded)
        self.items = items
        self.selcount = 0
        self.n = len(items)

    def OnClose(self):
        return

    def OnSelectLine(self, n):
        self.selcount += 1
        idc.jumpto(self.items[n][1])

    def OnGetLine(self, n):
        res = self.items[n]
        res = [str(res[0]), idc.atoa(res[1]), res[2], str(res[3])]
        return res

    def OnGetSize(self):
        return len(self.items)

    def show(self):
        return self.Show() >= 0


class AfxMSGMap(object):

    def __init__(self):
        self.cmin = 0
        self.cmax = 0
        self.rmin = 0
        self.rmax = 0
        self.dmin = 0
        self.dmax = 0
        self.msg_enum = 0
        self.MSGStructSize = 24
        self.USize = 4
        if idc.__EA64__:
            self.MSGStructSize = 32
            self.USize = 8

    @staticmethod
    def mt_rva():
        ri = ida_nalt.refinfo_t()
        if idc.__EA64__:
            ri.flags = idc.REF_OFF64
        else:
            ri.flags = idc.REF_OFF32
        ri.target = idc.BADADDR
        mt = ida_nalt.opinfo_t()
        mt.ri = ri
        return mt

    @staticmethod
    def mt_ascii():
        ri = ida_nalt.refinfo_t()
        ri.flags = ida_nalt.STRTYPE_C
        ri.target = idc.BADADDR
        mt = ida_nalt.opinfo_t()
        mt.ri = ri
        return mt

    def AddMSGMAPStruct(self):
        name = "AFX_MSGMAP"
        idx = idaapi.get_struc_id(name)
        if idx == idc.BADADDR:
            idx = idaapi.add_struc(idc.BADADDR, name)

            stru = idaapi.get_struc(idx)
            if idc.__EA64__:
                idaapi.add_struc_member(stru, "pfnGetBaseMap", 0, idc.FF_DATA | idc.FF_QWORD | idc.FF_0OFF, self.mt_rva(), 8)
                idaapi.add_struc_member(stru, "lpEntries", 8, idc.FF_DATA | idc.FF_QWORD | idc.FF_0OFF, self.mt_rva(), 8)
            else:
                idaapi.add_struc_member(stru, "pfnGetBaseMap", 0, idc.FF_DATA | idc.FF_DWORD | idc.FF_0OFF, self.mt_rva(), 4)
                idaapi.add_struc_member(stru, "lpEntries", 4, idc.FF_DATA | idc.FF_DWORD | idc.FF_0OFF, self.mt_rva(), 4)

        name = "AFX_MSGMAP_ENTRY"
        idx = idaapi.get_struc_id(name)
        if idx == idc.BADADDR:
            idx = idaapi.add_struc(idc.BADADDR, name)

            stru = idaapi.get_struc(idx)
            idaapi.add_struc_member(stru, "nMessage", 0, idc.FF_DATA | idc.FF_DWORD, None, 4)
            idaapi.add_struc_member(stru, "nCode", 4, idc.FF_DATA | idc.FF_DWORD, None, 4)
            idaapi.add_struc_member(stru, "nID", 8, idc.FF_DATA | idc.FF_DWORD, None, 4)
            idaapi.add_struc_member(stru, "nLastID", 12, idc.FF_DATA | idc.FF_DWORD, None, 4)

            if idc.__EA64__:
                idaapi.add_struc_member(stru, "nSig", 16, idc.FF_DATA | idc.FF_QWORD, None, 8)
                idaapi.add_struc_member(stru, "pfn", 24, idc.FF_DATA | idc.FF_QWORD | idc.FF_0OFF, self.mt_rva(), 8)
            else:
                idaapi.add_struc_member(stru, "nSig", 16, idc.FF_DATA | idc.FF_DWORD, None, 4)
                idaapi.add_struc_member(stru, "pfn", 20, idc.FF_DATA | idc.FF_DWORD | idc.FF_0OFF, self.mt_rva(), 4)

        return 0

    @staticmethod
    def GetMsgName(msgid):
        MSG_TABLES = {
            -2: "CB_ERRSPACE",
            -2: "LB_ERRSPACE",
            -1: "LB_ERR",
            -1: "CB_ERR",
            0x0: "CB_OKAY",
            0x0: "LB_OKAY",
            0x0: "WM_NULL",
            0x1: "WM_CREATE",
            0x2: "WM_DESTROY",
            0x3: "WM_MOVE",
            0x4: "WM_SIZEWAIT",
            0x5: "WM_SIZE",
            0x6: "WM_ACTIVATE",
            0x7: "WM_SETFOCUS",
            0x8: "WM_KILLFOCUS",
            0x9: "WM_SETVISIBLE",
            0xA: "WM_ENABLE",
            0xB: "WM_SETREDRAW",
            0xC: "WM_SETTEXT",
            0xD: "WM_GETTEXT",
            0xE: "WM_GETTEXTLENGTH",
            0xF: "WM_PAINT",
            0x10: "WM_CLOSE",
            0x11: "WM_QUERYENDSESSION",
            0x12: "WM_QUIT",
            0x13: "WM_QUERYOPEN",
            0x14: "WM_ERASEBKGND",
            0x15: "WM_SYSCOLORCHANGE",
            0x16: "WM_ENDSESSION",
            0x17: "WM_SYSTEMERROR",
            0x18: "WM_SHOWWINDOW",
            0x19: "WM_CTLCOLOR",
            0x1A: "WM_SETTINGCHANGE",
            0x1A: "WM_WININICHANGE",
            0x1B: "WM_DEVMODECHANGE",
            0x1C: "WM_ACTIVATEAPP",
            0x1D: "WM_FONTCHANGE",
            0x1E: "WM_TIMECHANGE",
            0x1F: "WM_CANCELMODE",
            0x20: "WM_SETCURSOR",
            0x21: "WM_MOUSEACTIVATE",
            0x22: "WM_CHILDACTIVATE",
            0x23: "WM_QUEUESYNC",
            0x24: "WM_GETMINMAXINFO",
            0x25: "WM_LOGOFF",
            0x26: "WM_PAINTICON",
            0x27: "WM_ICONERASEBKGND",
            0x28: "WM_NEXTDLGCTL",
            0x29: "WM_ALTTABACTIVE",
            0x2A: "WM_SPOOLERSTATUS",
            0x2B: "WM_DRAWITEM",
            0x2C: "WM_MEASUREITEM",
            0x2D: "WM_DELETEITEM",
            0x2E: "WM_VKEYTOITEM",
            0x2F: "WM_CHARTOITEM",
            0x30: "WM_SETFONT",
            0x31: "WM_GETFONT",
            0x32: "WM_SETHOTKEY",
            0x33: "WM_GETHOTKEY",
            0x34: "WM_FILESYSCHANGE",
            0x35: "WM_ISACTIVEICON",
            0x36: "WM_QUERYPARKICON",
            0x37: "WM_QUERYDRAGICON",
            0x38: "WM_WINHELP",
            0x39: "WM_COMPAREITEM",
            0x3A: "WM_FULLSCREEN",
            0x3B: "WM_CLIENTSHUTDOWN",
            0x3C: "WM_DDEMLEVENT",
            0x3D: "WM_GETOBJECT",
            0x3F: "MM_CALCSCROLL",
            0x40: "WM_TESTING",
            0x41: "WM_COMPACTING",
            0x42: "WM_OTHERWINDOWCREATED",
            0x43: "WM_OTHERWINDOWDESTROYED",
            0x44: "WM_COMMNOTIFY",
            0x45: "WM_MEDIASTATUSCHANGE",
            0x46: "WM_WINDOWPOSCHANGING",
            0x47: "WM_WINDOWPOSCHANGED",
            0x48: "WM_POWER",
            0x49: "WM_COPYGLOBALDATA",
            0x4A: "WM_COPYDATA",
            0x4B: "WM_CANCELJOURNAL",
            0x4C: "WM_LOGONNOTIFY",
            0x4D: "WM_KEYF1",
            0x4E: "WM_NOTIFY",
            0x4F: "WM_ACCESS_WINDOW",
            0x50: "WM_INPUTLANGCHANGEREQUEST",
            0x51: "WM_INPUTLANGCHANGE",
            0x52: "WM_TCARD",
            0x53: "WM_HELP",
            0x54: "WM_USERCHANGED",
            0x55: "WM_NOTIFYFORMAT",
            0x60: "WM_QM_ACTIVATE",
            0x61: "WM_HOOK_DO_CALLBACK",
            0x62: "WM_SYSCOPYDATA",
            0x70: "WM_FINALDESTROY",
            0x71: "WM_MEASUREITEM_CLIENTDATA",
            0x7B: "WM_CONTEXTMENU",
            0x7C: "WM_STYLECHANGING",
            0x7D: "WM_STYLECHANGED",
            0x7E: "WM_DISPLAYCHANGE",
            0x7F: "WM_GETICON",
            0x80: "WM_SETICON",
            0x81: "WM_NCCREATE",
            0x82: "WM_NCDESTROY",
            0x83: "WM_NCCALCSIZE",
            0x84: "WM_NCHITTEST",
            0x85: "WM_NCPAINT",
            0x86: "WM_NCACTIVATE",
            0x87: "WM_GETDLGCODE",
            0x88: "WM_SYNCPAINT",
            0x89: "WM_SYNCTASK",
            0xA0: "WM_NCMOUSEMOVE",
            0xA1: "WM_NCLBUTTONDOWN",
            0xA2: "WM_NCLBUTTONUP",
            0xA3: "WM_NCLBUTTONDBLCLK",
            0xA4: "WM_NCRBUTTONDOWN",
            0xA5: "WM_NCRBUTTONUP",
            0xA6: "WM_NCRBUTTONDBLCLK",
            0xA7: "WM_NCMBUTTONDOWN",
            0xA8: "WM_NCMBUTTONUP",
            0xA9: "WM_NCMBUTTONDBLCLK",
            0xAB: "WM_NCXBUTTONDOWN",
            0xAC: "WM_NCXBUTTONUP",
            0xAD: "WM_NCXBUTTONDBLCLK",
            0xB0: "EM_GETSEL",
            0xB1: "EM_SETSEL",
            0xB2: "EM_GETRECT",
            0xB3: "EM_SETRECT",
            0xB4: "EM_SETRECTNP",
            0xB5: "EM_SCROLL",
            0xB6: "EM_LINESCROLL",
            0xB7: "EM_SCROLLCARET",
            0xB8: "EM_GETMODIFY",
            0xB8: "IE_GETMODIFY",
            0xB9: "EM_SETMODIFY",
            0xB9: "IE_SETMODIFY",
            0xBA: "EM_GETLINECOUNT",
            0xBB: "EM_LINEINDEX",
            0xBC: "EM_SETHANDLE",
            0xBD: "EM_GETHANDLE",
            0xBE: "EM_GETTHUMB",
            0xC1: "EM_LINELENGTH",
            0xC2: "EM_REPLACESEL",
            0xC3: "EM_SETFONT",
            0xC4: "EM_GETLINE",
            0xC5: "EM_LIMITTEXT",
            0xC5: "EM_SETLIMITTEXT",
            0xC6: "EM_CANUNDO",
            0xC6: "IE_CANUNDO",
            0xC7: "EM_UNDO",
            0xC7: "IE_UNDO",
            0xC8: "EM_FMTLINES",
            0xC9: "EM_LINEFROMCHAR",
            0xCA: "EM_SETWORDBREAK",
            0xCB: "EM_SETTABSTOPS",
            0xCC: "EM_SETPASSWORDCHAR",
            0xCD: "EM_EMPTYUNDOBUFFER",
            0xCD: "IE_EMPTYUNDOBUFFER",
            0xCE: "EM_GETFIRSTVISIBLELINE",
            0xCF: "EM_SETREADONLY",
            0xD0: "EM_SETWORDBREAKPROC",
            0xD1: "EM_GETWORDBREAKPROC",
            0xD2: "EM_GETPASSWORDCHAR",
            0xD3: "EM_SETMARGINS",
            0xD4: "EM_GETMARGINS",
            0xD5: "EM_GETLIMITTEXT",
            0xD6: "EM_POSFROMCHAR",
            0xD7: "EM_CHARFROMPOS",
            0xD8: "EM_SETIMESTATUS",
            0xD9: "EM_GETIMESTATUS",
            0xE0: "SBM_SETPOS",
            0xE1: "SBM_GETPOS",
            0xE2: "SBM_SETRANGE",
            0xE3: "SBM_GETRANGE",
            0xE4: "SBM_ENABLE_ARROWS",
            0xE6: "SBM_SETRANGEREDRAW",
            0xE9: "SBM_SETSCROLLINFO",
            0xEA: "SBM_GETSCROLLINFO",
            0xEB: "SBM_GETSCROLLBARINFO",
            0xF0: "BM_GETCHECK",
            0xF1: "BM_SETCHECK",
            0xF2: "BM_GETSTATE",
            0xF3: "BM_SETSTATE",
            0xF4: "BM_SETSTYLE",
            0xF5: "BM_CLICK",
            0xF6: "BM_GETIMAGE",
            0xF7: "BM_SETIMAGE",
            0xF8: "BM_SETDONTCLICK",
            0xFE: "WM_INPUT_DEVICE_CHANGE",
            0xFF: "WM_INPUT",
            0x100: "WM_KEYDOWN",
            0x100: "WM_KEYFIRST",
            0x101: "WM_KEYUP",
            0x102: "WM_CHAR",
            0x103: "WM_DEADCHAR",
            0x104: "WM_SYSKEYDOWN",
            0x105: "WM_SYSKEYUP",
            0x106: "WM_SYSCHAR",
            0x107: "WM_SYSDEADCHAR",
            0x108: "WM_KEYLAST_PRE501",
            0x108: "WM_YOMICHAR",
            0x109: "WM_KEYLAST_NT501",
            0x109: "WM_KEYLAST",
            0x109: "WM_UNICHAR",
            0x109: "WM_WNT_CONVERTREQUESTEX",
            0x10A: "WM_CONVERTREQUEST",
            0x10B: "WM_CONVERTRESULT",
            0x10C: "WM_IM_INFO",
            0x10C: "WM_INTERIM",
            0x10D: "WM_IME_STARTCOMPOSITION",
            0x10E: "WM_IME_ENDCOMPOSITION",
            0x10F: "WM_IME_COMPOSITION",
            0x10F: "WM_IME_KEYLAST",
            0x110: "WM_INITDIALOG",
            0x111: "WM_COMMAND",
            0x112: "WM_SYSCOMMAND",
            0x113: "WM_TIMER",
            0x114: "WM_HSCROLL",
            0x115: "WM_VSCROLL",
            0x116: "WM_INITMENU",
            0x117: "WM_INITMENUPOPUP",
            0x118: "WM_SYSTIMER",
            0x119: "WM_GESTURE",
            0x11A: "WM_GESTURENOTIFY",
            0x11F: "WM_MENUSELECT",
            0x120: "WM_MENUCHAR",
            0x121: "WM_ENTERIDLE",
            0x122: "WM_MENURBUTTONUP",
            0x123: "WM_MENUDRAG",
            0x124: "WM_MENUGETOBJECT",
            0x125: "WM_UNINITMENUPOPUP",
            0x126: "WM_MENUCOMMAND",
            0x127: "WM_KEYBOARDCUES",
            0x127: "WM_CHANGEUISTATE",
            0x128: "WM_UPDATEUISTATE",
            0x129: "WM_QUERYUISTATE",
            0x131: "WM_LBTRACKPOINT",
            0x132: "WM_CTLCOLORMSGBOX",
            0x133: "WM_CTLCOLOREDIT",
            0x134: "WM_CTLCOLORLISTBOX",
            0x135: "WM_CTLCOLORBTN",
            0x136: "WM_CTLCOLORDLG",
            0x137: "WM_CTLCOLORSCROLLBAR",
            0x138: "WM_CTLCOLORSTATIC",
            0x140: "CB_GETEDITSEL",
            0x141: "CB_LIMITTEXT",
            0x142: "CB_SETEDITSEL",
            0x143: "CB_ADDSTRING",
            0x144: "CB_DELETESTRING",
            0x144: "CBEM_DELETEITEM",
            0x145: "CB_DIR",
            0x146: "CB_GETCOUNT",
            0x147: "CB_GETCURSEL",
            0x148: "CB_GETLBTEXT",
            0x149: "CB_GETLBTEXTLEN",
            0x14A: "CB_INSERTSTRING",
            0x14B: "CB_RESETCONTENT",
            0x14C: "CB_FINDSTRING",
            0x14D: "CB_SELECTSTRING",
            0x14E: "CB_SETCURSEL",
            0x14F: "CB_SHOWDROPDOWN",
            0x150: "CB_GETITEMDATA",
            0x151: "CB_SETITEMDATA",
            0x152: "CB_GETDROPPEDCONTROLRECT",
            0x153: "CB_SETITEMHEIGHT",
            0x154: "CB_GETITEMHEIGHT",
            0x155: "CB_SETEXTENDEDUI",
            0x156: "CB_GETEXTENDEDUI",
            0x157: "CB_GETDROPPEDSTATE",
            0x158: "CB_FINDSTRINGEXACT",
            0x159: "CB_SETLOCALE",
            0x15A: "CB_GETLOCALE",
            0x15B: "CB_GETTOPINDEX",
            0x15C: "CB_SETTOPINDEX",
            0x15D: "CB_GETHORIZONTALEXTENT",
            0x15E: "CB_SETHORIZONTALEXTENT",
            0x15F: "CB_GETDROPPEDWIDTH",
            0x160: "CB_SETDROPPEDWIDTH",
            0x161: "CB_INITSTORAGE",
            0x163: "CB_MSGMAX",
            0x163: "CB_MULTIPLEADDSTRING",
            0x164: "CB_GETCOMBOBOXINFO",
            0x170: "STM_SETICON",
            0x171: "STM_GETICON",
            0x172: "STM_SETIMAGE",
            0x173: "STM_GETIMAGE",
            0x174: "STM_MSGMAX",
            0x180: "LB_ADDSTRING",
            0x181: "LB_INSERTSTRING",
            0x182: "LB_DELETESTRING",
            0x183: "LB_SELITEMRANGEEX",
            0x184: "LB_RESETCONTENT",
            0x185: "LB_SETSEL",
            0x186: "LB_SETCURSEL",
            0x187: "LB_GETSEL",
            0x188: "LB_GETCURSEL",
            0x189: "LB_GETTEXT",
            0x18A: "LB_GETTEXTLEN",
            0x18B: "LB_GETCOUNT",
            0x18C: "LB_SELECTSTRING",
            0x18D: "LB_DIR",
            0x18E: "LB_GETTOPINDEX",
            0x18F: "LB_FINDSTRING",
            0x190: "LB_GETSELCOUNT",
            0x191: "LB_GETSELITEMS",
            0x192: "LB_SETTABSTOPS",
            0x193: "LB_GETHORIZONTALEXTENT",
            0x194: "LB_SETHORIZONTALEXTENT",
            0x195: "LB_SETCOLUMNWIDTH",
            0x196: "LB_ADDFILE",
            0x197: "LB_SETTOPINDEX",
            0x198: "LB_GETITEMRECT",
            0x199: "LB_GETITEMDATA",
            0x19A: "LB_SETITEMDATA",
            0x19B: "LB_SELITEMRANGE",
            0x19C: "LB_SETANCHORINDEX",
            0x19D: "LB_GETANCHORINDEX",
            0x19E: "LB_SETCARETINDEX",
            0x19F: "LB_GETCARETINDEX",
            0x1A0: "LB_SETITEMHEIGHT",
            0x1A1: "LB_GETITEMHEIGHT",
            0x1A2: "LB_FINDSTRINGEXACT",
            0x1A3: "LBCB_CARETON",
            0x1A4: "LBCB_CARETOFF",
            0x1A5: "LB_SETLOCALE",
            0x1A6: "LB_GETLOCALE",
            0x1A7: "LB_SETCOUNT",
            0x1A8: "LB_INITSTORAGE",
            0x1A9: "LB_ITEMFROMPOINT",
            0x1AA: "LB_INSERTSTRINGUPPER",
            0x1AB: "LB_INSERTSTRINGLOWER",
            0x1AC: "LB_ADDSTRINGUPPER",
            0x1AD: "LB_ADDSTRINGLOWER",
            0x1B1: "LB_MULTIPLEADDSTRING",
            0x1B1: "LB_MSGMAX",
            0x1B2: "LB_GETLISTBOXINFO",
            0x1E0: "MN_SETHMENU",
            0x1E1: "MN_GETHMENU",
            0x1E2: "MN_SIZEWINDOW",
            0x1E3: "MN_OPENHIERARCHY",
            0x1E4: "MN_CLOSEHIERARCHY",
            0x1E5: "MN_SELECTITEM",
            0x1E6: "MN_CANCELMENUS",
            0x1E7: "MN_SELECTFIRSTVALIDITEM",
            0x1EA: "MN_GETPPOPUPMENU",
            0x1EB: "MN_FINDMENUWINDOWFROMPOINT",
            0x1EC: "MN_SHOWPOPUPWINDOW",
            0x1ED: "MN_BUTTONDOWN",
            0x1EE: "MN_MOUSEMOVE",
            0x1EF: "MN_BUTTONUP",
            0x1F0: "MN_SETTIMERTOOPENHIERARCHY",
            0x1F1: "MN_DBLCLK",
            0x200: "WM_MOUSEFIRST",
            0x200: "WM_MOUSEMOVE",
            0x201: "WM_LBUTTONDOWN",
            0x202: "WM_LBUTTONUP",
            0x203: "WM_LBUTTONDBLCLK",
            0x204: "WM_RBUTTONDOWN",
            0x205: "WM_RBUTTONUP",
            0x206: "WM_RBUTTONDBLCLK",
            0x207: "WM_MBUTTONDOWN",
            0x208: "WM_MBUTTONUP",
            0x209: "WM_MBUTTONDBLCLK",
            0x20A: "WM_MOUSEWHEEL",
            0x20B: "WM_XBUTTONDOWN",
            0x20C: "WM_XBUTTONUP",
            0x20D: "WM_XBUTTONDBLCLK",
            0x20E: "WM_MOUSEHWHEEL",
            0x20E: "WM_MOUSELAST",
            0x210: "WM_PARENTNOTIFY",
            0x211: "WM_ENTERMENULOOP",
            0x212: "WM_EXITMENULOOP",
            0x213: "WM_NEXTMENU",
            0x214: "WM_SIZING",
            0x215: "WM_CAPTURECHANGED",
            0x216: "WM_MOVING",
            0x218: "WM_POWERBROADCAST",
            0x219: "WM_DEVICECHANGE",
            0x220: "WM_MDICREATE",
            0x221: "WM_MDIDESTROY",
            0x222: "WM_MDIACTIVATE",
            0x223: "WM_MDIRESTORE",
            0x224: "WM_MDINEXT",
            0x225: "WM_MDIMAXIMIZE",
            0x226: "WM_MDITILE",
            0x227: "WM_MDICASCADE",
            0x228: "WM_MDIICONARRANGE",
            0x229: "WM_MDIGETACTIVE",
            0x22A: "WM_DROPOBJECT",
            0x22B: "WM_QUERYDROPOBJECT",
            0x22C: "WM_BEGINDRAG",
            0x22D: "WM_DRAGLOOP",
            0x22E: "WM_DRAGSELECT",
            0x22F: "WM_DRAGMOVE",
            0x230: "WM_MDISETMENU",
            0x231: "WM_ENTERSIZEMOVE",
            0x232: "WM_EXITSIZEMOVE",
            0x233: "WM_DROPFILES",
            0x234: "WM_MDIREFRESHMENU",
            0x238: "WM_POINTERDEVICECHANGE",
            0x239: "WM_POINTERDEVICEINRANGE",
            0x23A: "WM_POINTERDEVICEOUTOFRANGE",
            0x240: "WM_TOUCH",
            0x241: "WM_NCPOINTERUPDATE",
            0x242: "WM_NCPOINTERDOWN",
            0x243: "WM_NCPOINTERUP",
            0x245: "WM_POINTERUPDATE",
            0x246: "WM_POINTERDOWN",
            0x247: "WM_POINTERUP",
            0x249: "WM_POINTERENTER",
            0x24A: "WM_POINTERLEAVE",
            0x24B: "WM_POINTERACTIVATE",
            0x24C: "WM_POINTERCAPTURECHANGED",
            0x24D: "WM_TOUCHHITTESTING",
            0x24E: "WM_POINTERWHEEL",
            0x24F: "WM_POINTERHWHEEL",
            0x251: "WM_POINTERROUTEDTO",
            0x252: "WM_POINTERROUTEDAWAY",
            0x253: "WM_POINTERROUTEDRELEASED",
            0x280: "WM_HANGEULFIRST",
            0x280: "WM_IME_REPORT",
            0x280: "WM_KANJIFIRST",
            0x281: "WM_IME_SETCONTEXT",
            0x282: "WM_IME_NOTIFY",
            0x283: "WM_IME_CONTROL",
            0x284: "WM_IME_COMPOSITIONFULL",
            0x285: "WM_IME_SELECT",
            0x286: "WM_IME_CHAR",
            0x287: "WM_IME_SYSTEM",
            0x288: "WM_IME_REQUEST",
            0x290: "WM_IME_KEYDOWN",
            0x290: "WM_IMEKEYDOWN",
            0x291: "WM_IME_KEYUP",
            0x291: "WM_IMEKEYUP",
            0x29F: "WM_HANGEULLAST",
            0x29F: "WM_KANJILAST",
            0x2A0: "WM_NCMOUSEHOVER",
            0x2A1: "WM_MOUSEHOVER",
            0x2A2: "WM_NCMOUSELEAVE",
            0x2A3: "WM_MOUSELEAVE",
            0x2AF: "WM_TRACKMOUSEEVENT_LAST",
            0x2B1: "WM_WTSSESSION_CHANGE",
            0x2C0: "WM_TABLET_FIRST",
            0x2C8: "WM_TABLET_ADDED",
            0x2C9: "WM_TABLET_DELETED",
            0x2CB: "WM_TABLET_FLICK",
            0x2CC: "WM_TABLET_QUERYSYSTEMGESTURESTATUS",
            0x2DF: "WM_TABLET_LAST",
            0x2E0: "WM_DPICHANGED",
            0x2E2: "WM_DPICHANGED_BEFOREPARENT",
            0x2E3: "WM_DPICHANGED_AFTERPARENT",
            0x2E4: "WM_GETDPISCALEDSIZE",
            0x300: "WM_CUT",
            0x301: "WM_COPY",
            0x302: "WM_PASTE",
            0x303: "WM_CLEAR",
            0x304: "WM_UNDO",
            0x305: "WM_RENDERFORMAT",
            0x306: "WM_RENDERALLFORMATS",
            0x307: "WM_DESTROYCLIPBOARD",
            0x308: "WM_DRAWCLIPBOARD",
            0x309: "WM_PAINTCLIPBOARD",
            0x30A: "WM_VSCROLLCLIPBOARD",
            0x30B: "WM_SIZECLIPBOARD",
            0x30C: "WM_ASKCBFORMATNAME",
            0x30D: "WM_CHANGECBCHAIN",
            0x30E: "WM_HSCROLLCLIPBOARD",
            0x30F: "WM_QUERYNEWPALETTE",
            0x310: "WM_PALETTEISCHANGING",
            0x311: "WM_PALETTECHANGED",
            0x312: "WM_HOTKEY",
            0x313: "WM_SYSMENU",
            0x314: "WM_HOOKMSG",
            0x315: "WM_EXITPROCESS",
            0x316: "WM_WAKETHREAD",
            0x317: "WM_PRINT",
            0x318: "WM_PRINTCLIENT",
            0x319: "WM_APPCOMMAND",
            0x31A: "WM_THEMECHANGED",
            0x31D: "WM_CLIPBOARDUPDATE",
            0x31E: "WM_DWMCOMPOSITIONCHANGED",
            0x31F: "WM_DWMNCRENDERINGCHANGED",
            0x320: "WM_DWMCOLORIZATIONCOLORCHANGED",
            0x321: "WM_DWMWINDOWMAXIMIZEDCHANGE",
            0x323: "WM_DWMSENDICONICTHUMBNAIL",
            0x326: "WM_DWMSENDICONICLIVEPREVIEWBITMAP",
            0x33F: "WM_GETTITLEBARINFOEX",
            0x358: "WM_HANDHELDFIRST",
            0x35F: "WM_HANDHELDLAST",
            # HTC - Internal AFX Windows messages, see in afxpriv.h file
            0x360: "WM_QUERYAFXWNDPROC",
            0x361: "WM_SIZEPARENT",

            0x37F: "WM_AFXLAST",
            0x380: "WM_PENWINFIRST",
            0x381: "WM_RCRESULT",
            0x382: "WM_HOOKRCRESULT",
            0x383: "WM_GLOBALRCCHANGE",
            0x383: "WM_PENMISCINFO",
            0x384: "WM_SKB",
            0x385: "WM_HEDITCTL",
            0x385: "WM_PENCTL",
            0x386: "WM_PENMISC",
            0x387: "WM_CTLINIT",
            0x388: "WM_PENEVENT",
            0x38F: "WM_PENWINLAST",
            0x390: "WM_COALESCE_FIRST",
            0x390: "WM_INTERNAL_COALESCE_FIRST",
            0x39F: "WM_COALESCE_LAST",
            0x3A0: "WM_MM_RESERVED_FIRST",
            0x3B0: "WM_INTERNAL_COALESCE_LAST",
            0x3DF: "WM_MM_RESERVED_LAST",
            0x3E0: "WM_DDE_FIRST",
            0x3E0: "WM_DDE_INITIATE",
            0x3E1: "WM_DDE_TERMINATE",
            0x3E2: "WM_DDE_ADVISE",
            0x3E3: "WM_DDE_UNADVISE",
            0x3E4: "WM_DDE_ACK",
            0x3E5: "WM_DDE_DATA",
            0x3E6: "WM_DDE_REQUEST",
            0x3E7: "WM_DDE_POKE",
            0x3E8: "WM_DDE_EXECUTE",
            0x3E8: "WM_DDE_LAST",
            0x3FD: "WM_DBNOTIFICATION",
            0x3FE: "WM_NETCONNECT",
            0x3FF: "WM_HIBERNATE",
            0x400: "DDM_SETFMT",
            0x400: "DM_GETDEFID",
            0x400: "NIN_SELECT",
            0x400: "TBM_GETPOS",
            0x400: "WM_CAP_START",
            0x400: "WM_PSD_PAGESETUPDLG",
            0x400: "WM_USER",
            0x401: "CBEM_INSERTITEMA",
            0x401: "DDM_DRAW",
            0x401: "DM_SETDEFID",
            0x401: "HKM_SETHOTKEY",
            0x401: "NIN_KEYSELECT",
            0x401: "PBM_SETRANGE",
            0x401: "RB_INSERTBANDA",
            0x401: "SB_SETTEXTA",
            0x401: "TB_ENABLEBUTTON",
            0x401: "TBM_GETRANGEMIN",
            0x401: "TTM_ACTIVATE",
            0x401: "WM_CAP_GET_CAPSTREAMPTR",
            0x401: "WM_CHOOSEFONT_GETLOGFONT",
            0x401: "WM_PSD_FULLPAGERECT",
            0x402: "CBEM_SETIMAGELIST",
            0x402: "DDM_CLOSE",
            0x402: "DM_REPOSITION",
            0x402: "HKM_GETHOTKEY",
            0x402: "NIN_BALLOONSHOW",
            0x402: "PBM_SETPOS",
            0x402: "RB_DELETEBAND",
            0x402: "SB_GETTEXTA",
            0x402: "TB_CHECKBUTTON",
            0x402: "TBM_GETRANGEMAX",
            0x402: "WM_CAP_SET_CALLBACK_ERRORA",
            0x402: "WM_PSD_MINMARGINRECT",
            0x403: "CBEM_GETIMAGELIST",
            0x403: "DDM_BEGIN",
            0x403: "HKM_SETRULES",
            0x403: "NIN_BALLOONHIDE",
            0x403: "PBM_DELTAPOS",
            0x403: "RB_GETBARINFO",
            0x403: "SB_GETTEXTLENGTHA",
            0x403: "TB_PRESSBUTTON",
            0x403: "TBM_GETTIC",
            0x403: "TTM_SETDELAYTIME",
            0x403: "WM_CAP_SET_CALLBACK_STATUSA",
            0x403: "WM_PSD_MARGINRECT",
            0x404: "CBEM_GETITEMA",
            0x404: "DDM_END",
            0x404: "NIN_BALLOONTIMEOUT",
            0x404: "PBM_SETSTEP",
            0x404: "RB_SETBARINFO",
            0x404: "SB_SETPARTS",
            0x404: "TB_HIDEBUTTON",
            0x404: "TBM_SETTIC",
            0x404: "TTM_ADDTOOLA",
            0x404: "WM_CAP_SET_CALLBACK_YIELD",
            0x404: "WM_PSD_GREEKTEXTRECT",
            0x405: "CBEM_SETITEMA",
            0x405: "NIN_BALLOONUSERCLICK",
            0x405: "PBM_STEPIT",
            0x405: "TB_INDETERMINATE",
            0x405: "TBM_SETPOS",
            0x405: "TTM_DELTOOLA",
            0x405: "WM_CAP_SET_CALLBACK_FRAME",
            0x405: "WM_PSD_ENVSTAMPRECT",
            0x406: "CBEM_GETCOMBOCONTROL",
            0x406: "NIN_POPUPOPEN",
            0x406: "PBM_SETRANGE32",
            0x406: "RB_SETBANDINFOA",
            0x406: "SB_GETPARTS",
            0x406: "TB_MARKBUTTON",
            0x406: "TBM_SETRANGE",
            0x406: "TTM_NEWTOOLRECTA",
            0x406: "WM_CAP_SET_CALLBACK_VIDEOSTREAM",
            0x406: "WM_PSD_YAFULLPAGERECT",
            0x407: "CBEM_GETEDITCONTROL",
            0x407: "NIN_POPUPCLOSE",
            0x407: "PBM_GETRANGE",
            0x407: "RB_SETPARENT",
            0x407: "SB_GETBORDERS",
            0x407: "TBM_SETRANGEMIN",
            0x407: "TTM_RELAYEVENT",
            0x407: "WM_CAP_SET_CALLBACK_WAVESTREAM",
            0x408: "CBEM_SETEXSTYLE",
            0x408: "PBM_GETPOS",
            0x408: "RB_HITTEST",
            0x408: "SB_SETMINHEIGHT",
            0x408: "TBM_SETRANGEMAX",
            0x408: "TTM_GETTOOLINFOA",
            0x408: "WM_CAP_GET_USER_DATA",
            0x409: "CBEM_GETEXSTYLE",
            0x409: "CBEM_GETEXTENDEDSTYLE",
            0x409: "PBM_SETBARCOLOR",
            0x409: "RB_GETRECT",
            0x409: "SB_SIMPLE",
            0x409: "TB_ISBUTTONENABLED",
            0x409: "TBM_CLEARTICS",
            0x409: "TTM_SETTOOLINFOA",
            0x409: "WM_CAP_SET_USER_DATA",
            0x40A: "CBEM_HASEDITCHANGED",
            0x40A: "PBM_SETMARQUEE",
            0x40A: "RB_INSERTBANDW",
            0x40A: "SB_GETRECT",
            0x40A: "TB_ISBUTTONCHECKED",
            0x40A: "TBM_SETSEL",
            0x40A: "TTM_HITTESTA",
            0x40A: "WIZ_QUERYNUMPAGES",
            0x40A: "WM_CAP_DRIVER_CONNECT",
            0x40B: "CBEM_INSERTITEMW",
            0x40B: "RB_SETBANDINFOW",
            0x40B: "SB_SETTEXTW",
            0x40B: "TB_ISBUTTONPRESSED",
            0x40B: "TBM_SETSELSTART",
            0x40B: "TTM_GETTEXTA",
            0x40B: "WIZ_NEXT",
            0x40B: "WM_CAP_DRIVER_DISCONNECT",
            0x40C: "CBEM_SETITEMW",
            0x40C: "RB_GETBANDCOUNT",
            0x40C: "SB_GETTEXTLENGTHW",
            0x40C: "TB_ISBUTTONHIDDEN",
            0x40C: "TBM_SETSELEND",
            0x40C: "TTM_UPDATETIPTEXTA",
            0x40C: "WIZ_PREV",
            0x40C: "WM_CAP_DRIVER_GET_NAMEA",
            0x40D: "CBEM_GETITEMW",
            0x40D: "PBM_GETSTEP",
            0x40D: "RB_GETROWCOUNT",
            0x40D: "SB_GETTEXTW",
            0x40D: "TB_ISBUTTONINDETERMINATE",
            0x40D: "TTM_GETTOOLCOUNT",
            0x40D: "WM_CAP_DRIVER_GET_VERSIONA",
            0x40E: "CBEM_SETEXTENDEDSTYLE",
            0x40E: "PBM_GETBKCOLOR",
            0x40E: "RB_GETROWHEIGHT",
            0x40E: "SB_ISSIMPLE",
            0x40E: "TB_ISBUTTONHIGHLIGHTED",
            0x40E: "TBM_GETPTICS",
            0x40E: "TTM_ENUMTOOLSA",
            0x40E: "WM_CAP_DRIVER_GET_CAPS",
            0x40F: "PBM_GETBARCOLOR",
            0x40F: "SB_SETICON",
            0x40F: "TBM_GETTICPOS",
            0x40F: "TTM_GETCURRENTTOOLA",
            0x410: "PBM_SETSTATE",
            0x410: "RB_IDTOINDEX",
            0x410: "SB_SETTIPTEXTA",
            0x410: "TBM_GETNUMTICS",
            0x410: "TTM_WINDOWFROMPOINT",
            0x411: "PBM_GETSTATE",
            0x411: "RB_GETTOOLTIPS",
            0x411: "SB_SETTIPTEXTW",
            0x411: "TB_SETSTATE",
            0x411: "TBM_GETSELSTART",
            0x411: "TTM_TRACKACTIVATE",
            0x412: "RB_SETTOOLTIPS",
            0x412: "SB_GETTIPTEXTA",
            0x412: "TB_GETSTATE",
            0x412: "TBM_GETSELEND",
            0x412: "TTM_TRACKPOSITION",
            0x413: "RB_SETBKCOLOR",
            0x413: "SB_GETTIPTEXTW",
            0x413: "TB_ADDBITMAP",
            0x413: "TBM_CLEARSEL",
            0x413: "TTM_SETTIPBKCOLOR",
            0x414: "RB_GETBKCOLOR",
            0x414: "SB_GETICON",
            0x414: "TB_ADDBUTTONSA",
            0x414: "TBM_SETTICFREQ",
            0x414: "TTM_SETTIPTEXTCOLOR",
            0x414: "WM_CAP_FILE_SET_CAPTURE_FILEA",
            0x415: "RB_SETTEXTCOLOR",
            0x415: "TB_INSERTBUTTONA",
            0x415: "TBM_SETPAGESIZE",
            0x415: "TTM_GETDELAYTIME",
            0x415: "WM_CAP_FILE_GET_CAPTURE_FILEA",
            0x416: "RB_GETTEXTCOLOR",
            0x416: "TB_DELETEBUTTON",
            0x416: "TBM_GETPAGESIZE",
            0x416: "TTM_GETTIPBKCOLOR",
            0x416: "WM_CAP_FILE_ALLOCATE",
            0x417: "RB_SIZETORECT",
            0x417: "TB_GETBUTTON",
            0x417: "TBM_SETLINESIZE",
            0x417: "TTM_GETTIPTEXTCOLOR",
            0x417: "WM_CAP_FILE_SAVEASA",
            0x418: "RB_BEGINDRAG",
            0x418: "TB_BUTTONCOUNT",
            0x418: "TBM_GETLINESIZE",
            0x418: "TTM_SETMAXTIPWIDTH",
            0x418: "WM_CAP_FILE_SET_INFOCHUNK",
            0x419: "RB_ENDDRAG",
            0x419: "TB_COMMANDTOINDEX",
            0x419: "TBM_GETTHUMBRECT",
            0x419: "TTM_GETMAXTIPWIDTH",
            0x419: "WM_CAP_FILE_SAVEDIBA",
            0x41A: "RB_DRAGMOVE",
            0x41A: "TB_SAVERESTOREA",
            0x41A: "TBM_GETCHANNELRECT",
            0x41A: "TTM_SETMARGIN",
            0x41B: "RB_GETBARHEIGHT",
            0x41B: "TB_CUSTOMIZE",
            0x41B: "TBM_SETTHUMBLENGTH",
            0x41B: "TTM_GETMARGIN",
            0x41C: "RB_GETBANDINFOW",
            0x41C: "TB_ADDSTRINGA",
            0x41C: "TBM_GETTHUMBLENGTH",
            0x41C: "TTM_POP",
            0x41D: "RB_GETBANDINFOA",
            0x41D: "TB_GETITEMRECT",
            0x41D: "TBM_SETTOOLTIPS",
            0x41D: "TTM_UPDATE",
            0x41E: "RB_MINIMIZEBAND",
            0x41E: "TB_BUTTONSTRUCTSIZE",
            0x41E: "TBM_GETTOOLTIPS",
            0x41E: "TTM_GETBUBBLESIZE",
            0x41E: "WM_CAP_EDIT_COPY",
            0x41F: "RB_MAXIMIZEBAND",
            0x41F: "TB_SETBUTTONSIZE",
            0x41F: "TBM_SETTIPSIDE",
            0x41F: "TTM_ADJUSTRECT",
            0x420: "MSG_FTS_JUMP_HASH",
            0x420: "TB_SETBITMAPSIZE",
            0x420: "TBM_SETBUDDY",
            0x420: "TTM_SETTITLEA",
            0x421: "MSG_FTS_JUMP_VA",
            0x421: "TB_AUTOSIZE",
            0x421: "TBM_GETBUDDY",
            0x421: "TTM_SETTITLEW",
            0x422: "MSG_FTS_GET_TITLE",
            0x422: "RB_GETBANDBORDERS",
            0x422: "TBM_SETPOSNOTIFY",
            0x423: "MSG_FTS_JUMP_QWORD",
            0x423: "RB_SHOWBAND",
            0x423: "TB_GETTOOLTIPS",
            0x423: "WM_CAP_SET_AUDIOFORMAT",
            0x424: "MSG_REINDEX_REQUEST",
            0x424: "TB_SETTOOLTIPS",
            0x424: "WM_CAP_GET_AUDIOFORMAT",
            0x425: "MSG_FTS_WHERE_IS_IT",
            0x425: "RB_SETPALETTE",
            0x425: "TB_SETPARENT",
            0x426: "RB_GETPALETTE",
            0x427: "RB_MOVEBAND",
            0x427: "TB_SETROWS",
            0x428: "RB_GETBANDMARGINS",
            0x428: "TB_GETROWS",
            0x429: "RB_SETEXTENDEDSTYLE",
            0x429: "TB_GETBITMAPFLAGS",
            0x429: "WM_CAP_DLG_VIDEOFORMAT",
            0x42A: "RB_GETEXTENDEDSTYLE",
            0x42A: "TB_SETCMDID",
            0x42A: "WM_CAP_DLG_VIDEOSOURCE",
            0x42B: "RB_PUSHCHEVRON",
            0x42B: "TB_CHANGEBITMAP",
            0x42B: "WM_CAP_DLG_VIDEODISPLAY",
            0x42C: "RB_SETBANDWIDTH",
            0x42C: "TB_GETBITMAP",
            0x42C: "WM_CAP_GET_VIDEOFORMAT",
            0x42D: "MSG_GET_DEFFONT",
            0x42D: "TB_GETBUTTONTEXTA",
            0x42D: "WM_CAP_SET_VIDEOFORMAT",
            0x42E: "TB_REPLACEBITMAP",
            0x42E: "WM_CAP_DLG_VIDEOCOMPRESSION",
            0x42F: "TB_SETINDENT",
            0x430: "TB_SETIMAGELIST",
            0x431: "TB_GETIMAGELIST",
            0x432: "EM_CANPASTE",
            0x432: "TB_LOADIMAGES",
            0x432: "TTM_ADDTOOLW",
            0x432: "WM_CAP_SET_PREVIEW",
            0x433: "EM_DISPLAYBAND",
            0x433: "TB_GETRECT",
            0x433: "TTM_DELTOOLW",
            0x433: "WM_CAP_SET_OVERLAY",
            0x434: "EM_EXGETSEL",
            0x434: "TB_SETHOTIMAGELIST",
            0x434: "TTM_NEWTOOLRECTW",
            0x434: "WM_CAP_SET_PREVIEWRATE",
            0x435: "EM_EXLIMITTEXT",
            0x435: "TB_GETHOTIMAGELIST",
            0x435: "TTM_GETTOOLINFOW",
            0x435: "WM_CAP_SET_SCALE",
            0x436: "EM_EXLINEFROMCHAR",
            0x436: "TB_SETDISABLEDIMAGELIST",
            0x436: "TTM_SETTOOLINFOW",
            0x436: "WM_CAP_GET_STATUS",
            0x437: "EM_EXSETSEL",
            0x437: "TB_GETDISABLEDIMAGELIST",
            0x437: "TTM_HITTESTW",
            0x437: "WM_CAP_SET_SCROLL",
            0x438: "EM_FINDTEXT",
            0x438: "TB_SETSTYLE",
            0x438: "TTM_GETTEXTW",
            0x439: "EM_FORMATRANGE",
            0x439: "TB_GETSTYLE",
            0x439: "TTM_UPDATETIPTEXTW",
            0x43A: "EM_GETCHARFORMAT",
            0x43A: "TB_GETBUTTONSIZE",
            0x43A: "TTM_ENUMTOOLSW",
            0x43B: "EM_GETEVENTMASK",
            0x43B: "TB_SETBUTTONWIDTH",
            0x43B: "TTM_GETCURRENTTOOLW",
            0x43C: "EM_GETOLEINTERFACE",
            0x43C: "TB_SETMAXTEXTROWS",
            0x43C: "WM_CAP_GRAB_FRAME",
            0x43D: "EM_GETPARAFORMAT",
            0x43D: "TB_GETTEXTROWS",
            0x43D: "WM_CAP_GRAB_FRAME_NOSTOP",
            0x43E: "EM_GETSELTEXT",
            0x43E: "TB_GETOBJECT",
            0x43E: "WM_CAP_SEQUENCE",
            0x43F: "EM_HIDESELECTION",
            0x43F: "TB_GETBUTTONINFOW",
            0x43F: "WM_CAP_SEQUENCE_NOFILE",
            0x440: "EM_PASTESPECIAL",
            0x440: "TB_SETBUTTONINFOW",
            0x440: "WM_CAP_SET_SEQUENCE_SETUP",
            0x441: "EM_REQUESTRESIZE",
            0x441: "TB_GETBUTTONINFOA",
            0x441: "WM_CAP_GET_SEQUENCE_SETUP",
            0x442: "EM_SELECTIONTYPE",
            0x442: "TB_SETBUTTONINFOA",
            0x442: "WM_CAP_SET_MCI_DEVICEA",
            0x443: "EM_SETBKGNDCOLOR",
            0x443: "TB_INSERTBUTTONW",
            0x443: "WM_CAP_GET_MCI_DEVICEA",
            0x444: "EM_SETCHARFORMAT",
            0x444: "TB_ADDBUTTONSW",
            0x444: "WM_CAP_STOP",
            0x445: "EM_SETEVENTMASK",
            0x445: "TB_HITTEST",
            0x445: "WM_CAP_ABORT",
            0x446: "EM_SETOLECALLBACK",
            0x446: "TB_SETDRAWTEXTFLAGS",
            0x446: "WM_CAP_SINGLE_FRAME_OPEN",
            0x447: "EM_SETPARAFORMAT",
            0x447: "TB_GETHOTITEM",
            0x447: "WM_CAP_SINGLE_FRAME_CLOSE",
            0x448: "EM_SETTARGETDEVICE",
            0x448: "TB_SETHOTITEM",
            0x448: "WM_CAP_SINGLE_FRAME",
            0x449: "EM_STREAMIN",
            0x449: "TB_SETANCHORHIGHLIGHT",
            0x44A: "EM_STREAMOUT",
            0x44A: "TB_GETANCHORHIGHLIGHT",
            0x44B: "EM_GETTEXTRANGE",
            0x44B: "TB_GETBUTTONTEXTW",
            0x44C: "EM_FINDWORDBREAK",
            0x44C: "TB_SAVERESTOREW",
            0x44D: "EM_SETOPTIONS",
            0x44D: "TB_ADDSTRINGW",
            0x44E: "EM_GETOPTIONS",
            0x44E: "TB_MAPACCELERATORA",
            0x44F: "EM_FINDTEXTEX",
            0x44F: "TB_GETINSERTMARK",
            0x450: "EM_GETWORDBREAKPROCEX",
            0x450: "TB_SETINSERTMARK",
            0x450: "WM_CAP_PAL_OPENA",
            0x451: "EM_SETWORDBREAKPROCEX",
            0x451: "TB_INSERTMARKHITTEST",
            0x451: "WM_CAP_PAL_SAVEA",
            0x452: "EM_SETUNDOLIMIT",
            0x452: "TB_MOVEBUTTON",
            0x452: "WM_CAP_PAL_PASTE",
            0x453: "TB_GETMAXSIZE",
            0x453: "WM_CAP_PAL_AUTOCREATE",
            0x454: "EM_REDO",
            0x454: "TB_SETEXTENDEDSTYLE",
            0x454: "WM_CAP_PAL_MANUALCREATE",
            0x455: "EM_CANREDO",
            0x455: "TB_GETEXTENDEDSTYLE",
            0x455: "WM_CAP_SET_CALLBACK_CAPCONTROL",
            0x456: "EM_GETUNDONAME",
            0x456: "TB_GETPADDING",
            0x457: "EM_GETREDONAME",
            0x457: "TB_SETPADDING",
            0x458: "EM_STOPGROUPTYPING",
            0x458: "TB_SETINSERTMARKCOLOR",
            0x459: "EM_SETTEXTMODE",
            0x459: "TB_GETINSERTMARKCOLOR",
            0x45A: "EM_GETTEXTMODE",
            0x45A: "TB_MAPACCELERATORW",
            0x45B: "EM_AUTOURLDETECT",
            0x45B: "TB_GETSTRINGW",
            0x45C: "EM_GETAUTOURLDETECT",
            0x45C: "TB_GETSTRINGA",
            0x45D: "EM_SETPALETTE",
            0x45D: "TB_SETBOUNDINGSIZE",
            0x45E: "EM_GETTEXTEX",
            0x45E: "TB_SETHOTITEM2",
            0x45F: "EM_GETTEXTLENGTHEX",
            0x45F: "TB_HASACCELERATOR",
            0x460: "EM_SHOWSCROLLBAR",
            0x460: "TB_SETLISTGAP",
            0x461: "EM_SETTEXTEX",
            0x462: "TB_GETIMAGELISTCOUNT",
            0x463: "TAPI_REPLY",
            0x463: "TB_GETIDEALSIZE",
            0x464: "ACM_OPENA",
            0x464: "BFFM_SETSTATUSTEXTA",
            0x464: "CDM_FIRST",
            0x464: "CDM_GETSPEC",
            0x464: "EM_SETPUNCTUATION",
            0x464: "IPM_CLEARADDRESS",
            0x464: "MCIWNDM_GETDEVICEID",
            0x464: "WM_CAP_UNICODE_START",
            0x465: "ACM_PLAY",
            0x465: "BFFM_ENABLEOK",
            0x465: "CDM_GETFILEPATH",
            0x465: "EM_GETPUNCTUATION",
            0x465: "IPM_SETADDRESS",
            0x465: "MCIWNDM_SENDSTRINGA",
            0x465: "PSM_SETCURSEL",
            0x465: "TB_GETMETRICS",
            0x465: "UDM_SETRANGE",
            0x465: "WM_CHOOSEFONT_SETLOGFONT",
            0x466: "ACM_STOP",
            0x466: "BFFM_SETSELECTIONA",
            0x466: "CDM_GETFOLDERPATH",
            0x466: "EM_SETWORDWRAPMODE",
            0x466: "IPM_GETADDRESS",
            0x466: "MCIWNDM_GETPOSITIONA",
            0x466: "PSM_REMOVEPAGE",
            0x466: "TB_SETMETRICS",
            0x466: "UDM_GETRANGE",
            0x466: "WM_CAP_SET_CALLBACK_ERRORW",
            0x466: "WM_CHOOSEFONT_SETFLAGS",
            0x467: "ACM_OPENW",
            0x467: "BFFM_SETSELECTIONW",
            0x467: "CDM_GETFOLDERIDLIST",
            0x467: "EM_GETWORDWRAPMODE",
            0x467: "IPM_SETRANGE",
            0x467: "MCIWNDM_GETSTART",
            0x467: "PSM_ADDPAGE",
            0x467: "TB_GETITEMDROPDOWNRECT",
            0x467: "UDM_SETPOS",
            0x467: "WM_CAP_SET_CALLBACK_STATUSW",
            0x468: "ACM_ISPLAYING",
            0x468: "BFFM_SETSTATUSTEXTW",
            0x468: "CDM_SETCONTROLTEXT",
            0x468: "EM_SETIMECOLOR",
            0x468: "IPM_SETFOCUS",
            0x468: "MCIWNDM_GETLENGTH",
            0x468: "PSM_CHANGED",
            0x468: "TB_SETPRESSEDIMAGELIST",
            0x468: "UDM_GETPOS",
            0x469: "BFFM_SETOKTEXT",
            0x469: "CDM_HIDECONTROL",
            0x469: "EM_GETIMECOLOR",
            0x469: "IPM_ISBLANK",
            0x469: "MCIWNDM_GETEND",
            0x469: "PSM_RESTARTWINDOWS",
            0x469: "TB_GETPRESSEDIMAGELIST",
            0x469: "UDM_SETBUDDY",
            0x46A: "BFFM_SETEXPANDED",
            0x46A: "CDM_SETDEFEXT",
            0x46A: "EM_SETIMEOPTIONS",
            0x46A: "MCIWNDM_GETMODEA",
            0x46A: "PSM_REBOOTSYSTEM",
            0x46A: "UDM_GETBUDDY",
            0x46B: "EM_GETIMEOPTIONS",
            0x46B: "MCIWNDM_EJECT",
            0x46B: "PSM_CANCELTOCLOSE",
            0x46B: "UDM_SETACCEL",
            0x46C: "EM_CONVPOSITION",
            0x46C: "MCIWNDM_SETZOOM",
            0x46C: "PSM_QUERYSIBLINGS",
            0x46C: "UDM_GETACCEL",
            0x46D: "MCIWNDM_GETZOOM",
            0x46D: "PSM_UNCHANGED",
            0x46D: "UDM_SETBASE",
            0x46E: "MCIWNDM_SETVOLUME",
            0x46E: "PSM_APPLY",
            0x46E: "UDM_GETBASE",
            0x46F: "MCIWNDM_GETVOLUME",
            0x46F: "PSM_SETTITLEA",
            0x46F: "UDM_SETRANGE32",
            0x470: "MCIWNDM_SETSPEED",
            0x470: "PSM_SETWIZBUTTONS",
            0x470: "UDM_GETRANGE32",
            0x470: "WM_CAP_DRIVER_GET_NAMEW",
            0x471: "MCIWNDM_GETSPEED",
            0x471: "PSM_PRESSBUTTON",
            0x471: "UDM_SETPOS32",
            0x471: "WM_CAP_DRIVER_GET_VERSIONW",
            0x472: "MCIWNDM_SETREPEAT",
            0x472: "PSM_SETCURSELID",
            0x472: "UDM_GETPOS32",
            0x473: "MCIWNDM_GETREPEAT",
            0x473: "PSM_SETFINISHTEXTA",
            0x474: "PSM_GETTABCONTROL",
            0x475: "PSM_ISDIALOGMESSAGE",
            0x476: "MCIWNDM_REALIZE",
            0x476: "PSM_GETCURRENTPAGEHWND",
            0x477: "MCIWNDM_SETTIMEFORMATA",
            0x477: "PSM_INSERTPAGE",
            0x478: "EM_SETLANGOPTIONS",
            0x478: "MCIWNDM_GETTIMEFORMATA",
            0x478: "PSM_SETTITLEW",
            0x478: "WM_CAP_FILE_SET_CAPTURE_FILEW",
            0x479: "EM_GETLANGOPTIONS",
            0x479: "MCIWNDM_VALIDATEMEDIA",
            0x479: "PSM_SETFINISHTEXTW",
            0x479: "WM_CAP_FILE_GET_CAPTURE_FILEW",
            0x47A: "EM_GETIMECOMPMODE",
            0x47A: "MCIWNDM_PLAYFROM",
            0x47B: "EM_FINDTEXTW",
            0x47B: "MCIWNDM_PLAYTO",
            0x47B: "WM_CAP_FILE_SAVEASW",
            0x47C: "EM_FINDTEXTEXW",
            0x47C: "MCIWNDM_GETFILENAMEA",
            0x47D: "EM_RECONVERSION",
            0x47D: "MCIWNDM_GETDEVICEA",
            0x47D: "PSM_SETHEADERTITLEA",
            0x47D: "WM_CAP_FILE_SAVEDIBW",
            0x47E: "EM_SETIMEMODEBIAS",
            0x47E: "MCIWNDM_GETPALETTE",
            0x47E: "PSM_SETHEADERTITLEW",
            0x47F: "EM_GETIMEMODEBIAS",
            0x47F: "MCIWNDM_SETPALETTE",
            0x47F: "PSM_SETHEADERSUBTITLEA",
            0x480: "MCIWNDM_GETERRORA",
            0x480: "PSM_SETHEADERSUBTITLEW",
            0x481: "MCIWNDM_SETTIMERS",
            0x481: "PSM_HWNDTOINDEX",
            0x482: "MCIWNDM_SETACTIVETIMER",
            0x482: "PSM_INDEXTOHWND",
            0x483: "MCIWNDM_SETINACTIVETIMER",
            0x483: "PSM_PAGETOINDEX",
            0x484: "MCIWNDM_GETACTIVETIMER",
            0x484: "PSM_INDEXTOPAGE",
            0x485: "DL_BEGINDRAG",
            0x485: "MCIWNDM_GETINACTIVETIMER",
            0x485: "PSM_IDTOINDEX",
            0x486: "DL_DRAGGING",
            0x486: "MCIWNDM_NEWA",
            0x486: "PSM_INDEXTOID",
            0x487: "DL_DROPPED",
            0x487: "MCIWNDM_CHANGESTYLES",
            0x487: "PSM_GETRESULT",
            0x488: "DL_CANCELDRAG",
            0x488: "MCIWNDM_GETSTYLES",
            0x488: "PSM_RECALCPAGESIZES",
            0x489: "MCIWNDM_GETALIAS",
            0x489: "PSM_SETNEXTTEXTW",
            0x48A: "MCIWNDM_RETURNSTRINGA",
            0x48A: "PSM_SHOWWIZBUTTONS",
            0x48B: "MCIWNDM_PLAYREVERSE",
            0x48B: "PSM_ENABLEWIZBUTTONS",
            0x48C: "MCIWNDM_GET_SOURCE",
            0x48C: "PSM_SETBUTTONTEXTW",
            0x48D: "MCIWNDM_PUT_SOURCE",
            0x48E: "MCIWNDM_GET_DEST",
            0x48F: "MCIWNDM_PUT_DEST",
            0x490: "MCIWNDM_CAN_PLAY",
            0x491: "MCIWNDM_CAN_WINDOW",
            0x492: "MCIWNDM_CAN_RECORD",
            0x493: "MCIWNDM_CAN_SAVE",
            0x494: "MCIWNDM_CAN_EJECT",
            0x495: "MCIWNDM_CAN_CONFIG",
            0x496: "IE_GETINK",
            0x496: "IE_MSGFIRST",
            0x496: "MCIWNDM_PALETTEKICK",
            0x497: "IE_SETINK",
            0x497: "MCIWNDM_OPENINTERFACE",
            0x498: "IE_GETPENTIP",
            0x498: "MCIWNDM_SETOWNER",
            0x499: "IE_SETPENTIP",
            0x499: "MCIWNDM_OPENA",
            0x49A: "IE_GETERASERTIP",
            0x49B: "IE_SETERASERTIP",
            0x49C: "IE_GETBKGND",
            0x49D: "IE_SETBKGND",
            0x49E: "IE_GETGRIDORIGIN",
            0x49F: "IE_SETGRIDORIGIN",
            0x4A0: "IE_GETGRIDPEN",
            0x4A1: "IE_SETGRIDPEN",
            0x4A2: "IE_GETGRIDSIZE",
            0x4A3: "IE_SETGRIDSIZE",
            0x4A4: "IE_GETMODE",
            0x4A5: "IE_SETMODE",
            0x4A6: "IE_GETINKRECT",
            0x4A6: "WM_CAP_SET_MCI_DEVICEW",
            0x4A7: "WM_CAP_GET_MCI_DEVICEW",
            0x4B4: "WM_CAP_PAL_OPENW",
            0x4B5: "WM_CAP_END",
            0x4B5: "WM_CAP_PAL_SAVEW",
            0x4B5: "WM_CAP_UNICODE_END",
            0x4B8: "IE_GETAPPDATA",
            0x4B9: "IE_SETAPPDATA",
            0x4BA: "IE_GETDRAWOPTS",
            0x4BB: "IE_SETDRAWOPTS",
            0x4BC: "IE_GETFORMAT",
            0x4BD: "IE_SETFORMAT",
            0x4BE: "IE_GETINKINPUT",
            0x4BF: "IE_SETINKINPUT",
            0x4C0: "IE_GETNOTIFY",
            0x4C1: "IE_SETNOTIFY",
            0x4C2: "IE_GETRECOG",
            0x4C3: "IE_SETRECOG",
            0x4C4: "IE_GETSECURITY",
            0x4C5: "IE_SETSECURITY",
            0x4C6: "IE_GETSEL",
            0x4C7: "IE_SETSEL",
            0x4C8: "CDM_LAST",
            0x4C8: "EM_SETBIDIOPTIONS",
            0x4C8: "IE_DOCOMMAND",
            0x4C8: "MCIWNDM_NOTIFYMODE",
            0x4C9: "EM_GETBIDIOPTIONS",
            0x4C9: "IE_GETCOMMAND",
            0x4C9: "MCIWNDM_NOTIFYPOS",
            0x4C9: "MCIWNDM_SENDSTRINGW",
            0x4CA: "EM_SETTYPOGRAPHYOPTIONS",
            0x4CA: "IE_GETCOUNT",
            0x4CA: "MCIWNDM_GETPOSITIONW",
            0x4CA: "MCIWNDM_NOTIFYSIZE",
            0x4CB: "EM_GETTYPOGRAPHYOPTIONS",
            0x4CB: "IE_GETGESTURE",
            0x4CB: "MCIWNDM_NOTIFYMEDIA",
            0x4CC: "EM_SETEDITSTYLE",
            0x4CC: "IE_GETMENU",
            0x4CD: "EM_GETEDITSTYLE",
            0x4CD: "IE_GETPAINTDC",
            0x4CD: "MCIWNDM_NOTIFYERROR",
            0x4CE: "IE_GETPDEVENT",
            0x4CE: "MCIWNDM_GETMODEW",
            0x4CF: "IE_GETSELCOUNT",
            0x4D0: "IE_GETSELITEMS",
            0x4D1: "IE_GETSTYLE",
            0x4DB: "MCIWNDM_SETTIMEFORMATW",
            0x4DC: "EM_OUTLINE",
            0x4DC: "MCIWNDM_GETTIMEFORMATW",
            0x4DD: "EM_GETSCROLLPOS",
            0x4DE: "EM_SETSCROLLPOS",
            0x4DF: "EM_SETFONTSIZE",
            0x4E0: "EM_GETZOOM",
            0x4E0: "MCIWNDM_GETFILENAMEW",
            0x4E1: "EM_SETZOOM",
            0x4E1: "MCIWNDM_GETDEVICEW",
            0x4E2: "EM_GETVIEWKIND",
            0x4E3: "EM_SETVIEWKIND",
            0x4E4: "EM_GETPAGE",
            0x4E4: "MCIWNDM_GETERRORW",
            0x4E5: "EM_SETPAGE",
            0x4E6: "EM_GETHYPHENATEINFO",
            0x4E7: "EM_SETHYPHENATEINFO",
            0x4E8: "EM_INSERTTABLE",
            0x4E9: "EM_GETAUTOCORRECTPROC",
            0x4EA: "EM_SETAUTOCORRECTPROC",
            0x4EA: "MCIWNDM_NEWW",
            0x4EB: "EM_GETPAGEROTATE",
            0x4EC: "EM_SETPAGEROTATE",
            0x4ED: "EM_GETCTFMODEBIAS",
            0x4EE: "EM_SETCTFMODEBIAS",
            0x4EE: "MCIWNDM_RETURNSTRINGW",
            0x4F0: "EM_GETCTFOPENSTATUS",
            0x4F1: "EM_SETCTFOPENSTATUS",
            0x4F2: "EM_GETIMECOMPTEXT",
            0x4F3: "EM_ISIME",
            0x4F4: "EM_GETIMEPROPERTY",
            0x4FC: "MCIWNDM_OPENW",
            0x4FF: "EM_CALLAUTOCORRECTPROC",
            0x509: "EM_GETTABLEPARMS",
            0x50D: "EM_GETQUERYRTFOBJ",
            0x50E: "EM_SETQUERYRTFOBJ",
            0x513: "EM_SETEDITSTYLEEX",
            0x514: "EM_GETEDITSTYLEEX",
            0x522: "EM_GETSTORYTYPE",
            0x523: "EM_SETSTORYTYPE",
            0x531: "EM_GETELLIPSISMODE",
            0x532: "EM_SETELLIPSISMODE",
            0x533: "EM_SETTABLEPARMS",
            0x536: "EM_GETTOUCHOPTIONS",
            0x537: "EM_SETTOUCHOPTIONS",
            0x53A: "EM_INSERTIMAGE",
            0x540: "EM_SETUIANAME",
            0x542: "EM_GETELLIPSISSTATE",
            0x600: "FM_GETFOCUS",
            0x601: "FM_GETDRIVEINFOA",
            0x602: "FM_GETSELCOUNT",
            0x603: "FM_GETSELCOUNTLFN",
            0x604: "FM_GETFILESELA",
            0x605: "FM_GETFILESELLFNA",
            0x606: "FM_REFRESH_WINDOWS",
            0x607: "FM_RELOAD_EXTENSIONS",
            0x611: "FM_GETDRIVEINFOW",
            0x614: "FM_GETFILESELW",
            0x615: "FM_GETFILESELLFNW",
            0x659: "WLX_WM_SAS",
            0x7E8: "SM_GETSELCOUNT",
            0x7E8: "UM_GETSELCOUNT",
            0x7E8: "WM_CPL_LAUNCH",
            0x7E9: "SM_GETSERVERSELA",
            0x7E9: "UM_GETUSERSELA",
            0x7E9: "WM_CPL_LAUNCHED",
            0x7EA: "SM_GETSERVERSELW",
            0x7EA: "UM_GETUSERSELW",
            0x7EB: "SM_GETCURFOCUSA",
            0x7EB: "UM_GETGROUPSELA",
            0x7EC: "SM_GETCURFOCUSW",
            0x7EC: "UM_GETGROUPSELW",
            0x7ED: "SM_GETOPTIONS",
            0x7ED: "UM_GETCURFOCUSA",
            0x7EE: "UM_GETCURFOCUSW",
            0x7EF: "UM_GETOPTIONS",
            0x7F0: "UM_GETOPTIONS2",
            0x84D: "WM_ADSPROP_NOTIFY_PAGEINIT",
            0x84E: "WM_ADSPROP_NOTIFY_PAGEHWND",
            0x84F: "WM_ADSPROP_NOTIFY_CHANGE",
            0x850: "WM_ADSPROP_NOTIFY_APPLY",
            0x851: "WM_ADSPROP_NOTIFY_SETFOCUS",
            0x852: "WM_ADSPROP_NOTIFY_FOREGROUND",
            0x853: "WM_ADSPROP_NOTIFY_EXIT",
            0x856: "WM_ADSPROP_NOTIFY_ERROR",
            0x1000: "LVM_FIRST",
            0x1000: "LVM_GETBKCOLOR",
            0x1001: "LVM_SETBKCOLOR",
            0x1002: "LVM_GETIMAGELIST",
            0x1003: "LVM_SETIMAGELIST",
            0x1004: "LVM_GETITEMCOUNT",
            0x1005: "LVM_GETITEMA",
            0x1006: "LVM_SETITEMA",
            0x1007: "LVM_INSERTITEMA",
            0x1008: "LVM_DELETEITEM",
            0x1009: "LVM_DELETEALLITEMS",
            0x100A: "LVM_GETCALLBACKMASK",
            0x100B: "LVM_SETCALLBACKMASK",
            0x100C: "LVM_GETNEXTITEM",
            0x100D: "LVM_FINDITEMA",
            0x100E: "LVM_GETITEMRECT",
            0x100F: "LVM_SETITEMPOSITION",
            0x1010: "LVM_GETITEMPOSITION",
            0x1011: "LVM_GETSTRINGWIDTHA",
            0x1012: "LVM_HITTEST",
            0x1013: "LVM_ENSUREVISIBLE",
            0x1014: "LVM_SCROLL",
            0x1015: "LVM_REDRAWITEMS",
            0x1016: "LVM_ARRANGE",
            0x1017: "LVM_EDITLABELA",
            0x1018: "LVM_GETEDITCONTROL",
            0x1019: "LVM_GETCOLUMNA",
            0x101A: "LVM_SETCOLUMNA",
            0x101B: "LVM_INSERTCOLUMNA",
            0x101C: "LVM_DELETECOLUMN",
            0x101D: "LVM_GETCOLUMNWIDTH",
            0x101E: "LVM_SETCOLUMNWIDTH",
            0x101F: "LVM_GETHEADER",
            0x1021: "LVM_CREATEDRAGIMAGE",
            0x1022: "LVM_GETVIEWRECT",
            0x1023: "LVM_GETTEXTCOLOR",
            0x1024: "LVM_SETTEXTCOLOR",
            0x1025: "LVM_GETTEXTBKCOLOR",
            0x1026: "LVM_SETTEXTBKCOLOR",
            0x1027: "LVM_GETTOPINDEX",
            0x1028: "LVM_GETCOUNTPERPAGE",
            0x1029: "LVM_GETORIGIN",
            0x102A: "LVM_UPDATE",
            0x102B: "LVM_SETITEMSTATE",
            0x102C: "LVM_GETITEMSTATE",
            0x102D: "LVM_GETITEMTEXTA",
            0x102E: "LVM_SETITEMTEXTA",
            0x102F: "LVM_SETITEMCOUNT",
            0x1030: "LVM_SORTITEMS",
            0x1031: "LVM_SETITEMPOSITION32",
            0x1032: "LVM_GETSELECTEDCOUNT",
            0x1033: "LVM_GETITEMSPACING",
            0x1034: "LVM_GETISEARCHSTRINGA",
            0x1035: "LVM_SETICONSPACING",
            0x1036: "LVM_SETEXTENDEDLISTVIEWSTYLE",
            0x1037: "LVM_GETEXTENDEDLISTVIEWSTYLE",
            0x1038: "LVM_GETSUBITEMRECT",
            0x1039: "LVM_SUBITEMHITTEST",
            0x103A: "LVM_SETCOLUMNORDERARRAY",
            0x103B: "LVM_GETCOLUMNORDERARRAY",
            0x103C: "LVM_SETHOTITEM",
            0x103D: "LVM_GETHOTITEM",
            0x103E: "LVM_SETHOTCURSOR",
            0x103F: "LVM_GETHOTCURSOR",
            0x1040: "LVM_APPROXIMATEVIEWRECT",
            0x1041: "LVM_SETWORKAREAS",
            0x1042: "LVM_GETSELECTIONMARK",
            0x1043: "LVM_SETSELECTIONMARK",
            0x1044: "LVM_SETBKIMAGEA",
            0x1045: "LVM_GETBKIMAGEA",
            0x1046: "LVM_GETWORKAREAS",
            0x1047: "LVM_SETHOVERTIME",
            0x1048: "LVM_GETHOVERTIME",
            0x1049: "LVM_GETNUMBEROFWORKAREAS",
            0x104A: "LVM_SETTOOLTIPS",
            0x104B: "LVM_GETITEMW",
            0x104C: "LVM_SETITEMW",
            0x104D: "LVM_INSERTITEMW",
            0x104E: "LVM_GETTOOLTIPS",
            0x1051: "LVM_SORTITEMSEX",
            0x1053: "LVM_FINDITEMW",
            0x1057: "LVM_GETSTRINGWIDTHW",
            0x105C: "LVM_GETGROUPSTATE",
            0x105D: "LVM_GETFOCUSEDGROUP",
            0x105F: "LVM_GETCOLUMNW",
            0x1060: "LVM_SETCOLUMNW",
            0x1061: "LVM_INSERTCOLUMNW",
            0x1062: "LVM_GETGROUPRECT",
            0x1073: "LVM_GETITEMTEXTW",
            0x1074: "LVM_SETITEMTEXTW",
            0x1075: "LVM_GETISEARCHSTRINGW",
            0x1076: "LVM_EDITLABELW",
            0x108A: "LVM_SETBKIMAGEW",
            0x108B: "LVM_GETBKIMAGEW",
            0x108C: "LVM_SETSELECTEDCOLUMN",
            0x108D: "LVM_SETTILEWIDTH",
            0x108E: "LVM_SETVIEW",
            0x108F: "LVM_GETVIEW",
            0x1091: "LVM_INSERTGROUP",
            0x1093: "LVM_SETGROUPINFO",
            0x1095: "LVM_GETGROUPINFO",
            0x1096: "LVM_REMOVEGROUP",
            0x1097: "LVM_MOVEGROUP",
            0x1098: "LVM_GETGROUPCOUNT",
            0x1099: "LVM_GETGROUPINFOBYINDEX",
            0x109A: "LVM_MOVEITEMTOGROUP",
            0x109B: "LVM_SETGROUPMETRICS",
            0x109C: "LVM_GETGROUPMETRICS",
            0x109D: "LVM_ENABLEGROUPVIEW",
            0x109E: "LVM_SORTGROUPS",
            0x109F: "LVM_INSERTGROUPSORTED",
            0x10A0: "LVM_REMOVEALLGROUPS",
            0x10A1: "LVM_HASGROUP",
            0x10A2: "LVM_SETTILEVIEWINFO",
            0x10A3: "LVM_GETTILEVIEWINFO",
            0x10A4: "LVM_SETTILEINFO",
            0x10A5: "LVM_GETTILEINFO",
            0x10A6: "LVM_SETINSERTMARK",
            0x10A7: "LVM_GETINSERTMARK",
            0x10A8: "LVM_INSERTMARKHITTEST",
            0x10A9: "LVM_GETINSERTMARKRECT",
            0x10AA: "LVM_SETINSERTMARKCOLOR",
            0x10AB: "LVM_GETINSERTMARKCOLOR",
            0x10AD: "LVM_SETINFOTIP",
            0x10AE: "LVM_GETSELECTEDCOLUMN",
            0x10AF: "LVM_ISGROUPVIEWENABLED",
            0x10B0: "LVM_GETOUTLINECOLOR",
            0x10B1: "LVM_SETOUTLINECOLOR",
            0x10B3: "LVM_CANCELEDITLABEL",
            0x10B4: "LVM_MAPINDEXTOID",
            0x10B5: "LVM_MAPIDTOINDEX",
            0x10B6: "LVM_ISITEMVISIBLE",
            0x10CC: "LVM_GETEMPTYTEXT",
            0x10CD: "LVM_GETFOOTERRECT",
            0x10CE: "LVM_GETFOOTERINFO",
            0x10CF: "LVM_GETFOOTERITEMRECT",
            0x10D0: "LVM_GETFOOTERITEM",
            0x10D1: "LVM_GETITEMINDEXRECT",
            0x10D2: "LVM_SETITEMINDEXSTATE",
            0x10D3: "LVM_GETNEXTITEMINDEX",
            0x11EF: "WM_DLGBORDER",
            0x11F0: "WM_DLGSUBCLASS",
            0x1701: "CB_SETMINVISIBLE",
            0x1702: "CB_GETMINVISIBLE",
            0x1703: "CB_SETCUEBANNER",
            0x1704: "CB_GETCUEBANNER",
            0x2000: "OCM__BASE",
            0x2001: "PBM_SETBKCOLOR",
            0x2001: "SB_SETBKCOLOR",
            0x2002: "RB_SETCOLORSCHEME",
            0x2002: "TB_SETCOLORSCHEME",
            0x2003: "RB_GETCOLORSCHEME",
            0x2003: "TB_GETCOLORSCHEME",
            0x2004: "RB_GETDROPTARGET",
            0x2005: "CBEM_SETUNICODEFORMAT",
            0x2005: "LVM_SETUNICODEFORMAT",
            0x2005: "RB_SETUNICODEFORMAT",
            0x2005: "SB_SETUNICODEFORMAT",
            0x2005: "TB_SETUNICODEFORMAT",
            0x2005: "TBM_SETUNICODEFORMAT",
            0x2005: "UDM_SETUNICODEFORMAT",
            0x2006: "CBEM_GETUNICODEFORMAT",
            0x2006: "LVM_GETUNICODEFORMAT",
            0x2006: "RB_GETUNICODEFORMAT",
            0x2006: "SB_GETUNICODEFORMAT",
            0x2006: "TB_GETUNICODEFORMAT",
            0x2006: "TBM_GETUNICODEFORMAT",
            0x2006: "UDM_GETUNICODEFORMAT",
            0x0209: "WM_MOUSELAST_PRE_4",
            0x020A: "WM_MOUSELAST_4",
            0x200B: "RB_SETWINDOWTHEME",
            0x200B: "TB_SETWINDOWTHEME",
            0x020D: "WM_MOUSELAST_5",
            0x2019: "OCM_CTLCOLOR",
            0x202B: "OCM_DRAWITEM",
            0x202C: "OCM_MEASUREITEM",
            0x202D: "OCM_DELETEITEM",
            0x202E: "OCM_VKEYTOITEM",
            0x202F: "OCM_CHARTOITEM",
            0x2039: "OCM_COMPAREITEM",
            0x204E: "OCM_NOTIFY",
            0x2111: "OCM_COMMAND",
            0x2114: "OCM_HSCROLL",
            0x2115: "OCM_VSCROLL",
            0x2132: "OCM_CTLCOLORMSGBOX",
            0x2133: "OCM_CTLCOLOREDIT",
            0x2134: "OCM_CTLCOLORLISTBOX",
            0x2135: "OCM_CTLCOLORBTN",
            0x2136: "OCM_CTLCOLORDLG",
            0x2137: "OCM_CTLCOLORSCROLLBAR",
            0x2138: "OCM_CTLCOLORSTATIC",
            0x2210: "OCM_PARENTNOTIFY",
            0x8000: "WM_APP",
            0xC002: "STDOLEVERB",   # HTC - afxole.h
            0xCCCD: "WM_RASDIALEVENT",
        }

        return MSG_TABLES.get(msgid, "WM_USER_%#04LX" % msgid)

    def CheckMSGEntry_attr(self, entry):
        if entry == idc.BADADDR:
            return 0
        if idaapi.get_dword(entry + 8) > 65535:
            return 0
        if idaapi.get_dword(entry + 12) > 65535:
            return 0
        Sig = self.getAword(entry + 16)
        if Sig > 100:   # Sig
            if Sig < self.dmin or Sig > self.dmax:  # point message
                return 0

        return 1

    @staticmethod
    def getAword(addr, offset=0):
        return idaapi.get_qword(addr + offset * 8) if idc.__EA64__ else idaapi.get_dword(addr + offset * 4)

    @staticmethod
    def get_pfn(addr):
        return idaapi.get_qword(addr + 24) if idc.__EA64__ else idaapi.get_dword(addr + 20)

    def CheckMSGMAP(self, addr):
        addrGetThisMessageMap = self.getAword(addr, 0)
        addrMsgEntry = self.getAword(addr, 1)

        if self.CheckMSGEntry_attr(addrMsgEntry) == 0:
            return 0

        if self.cmax == 0 or self.rmax == 0 or self.dmax == 0:
            snum = ida_segment.get_segm_qty()

            for i in range(0, snum):
                s = ida_segment.getnseg(i)
                segname = ida_segment.get_segm_name(s)

                if segname == ".text":
                    self.cmin = s.start_ea
                    self.cmax = s.end_ea

                if segname == ".rdata":
                    self.rmin = s.start_ea
                    self.rmax = s.end_ea

                if segname == ".data":
                    self.dmin = s.start_ea
                    self.dmax = s.end_ea

        if self.cmin == self.cmax or self.cmax == 0:
            return 0
        if self.rmin == self.rmax or self.rmax == 0:
            return 0

        if addrGetThisMessageMap < self.cmin or addrGetThisMessageMap > self.cmax:
            #如果是静态连接的, 这里直接指向父消息表地址
            if addrGetThisMessageMap < self.rmin or addrGetThisMessageMap > self.rmax:
                return 0

        if addrMsgEntry < self.rmin or addrMsgEntry > self.rmax:
            return 0

        if idaapi.get_dword(addrMsgEntry + 0) == 0 and \
            (idaapi.get_dword(addrMsgEntry + 4) != 0 or
             idaapi.get_dword(addrMsgEntry + 8) != 0 or
             idaapi.get_dword(addrMsgEntry + 12) != 0 or
             self.getAword(addrMsgEntry + 16) != 0 or
             self.get_pfn(addrMsgEntry) != 0):
            return 0

        if idaapi.get_name(addr) == "":
            if idaapi.get_name(addrGetThisMessageMap) == "":
                return 0
            return -1

        if idaapi.get_name(addrGetThisMessageMap)[0:18] == "?GetThisMessageMap":
            return 1

        while addrMsgEntry != idc:
            if  idaapi.get_dword(addrMsgEntry + 0) == 0 and \
                idaapi.get_dword(addrMsgEntry + 4) == 0 and \
                idaapi.get_dword(addrMsgEntry + 8) == 0 and \
                idaapi.get_dword(addrMsgEntry + 12) == 0 and \
                self.getAword(addrMsgEntry + 16) == 0 and \
                self.get_pfn(addrMsgEntry) == 0:
                return 1

            if self.CheckMSGEntry_attr(addrMsgEntry) == 0:
                return 0

            msgfun_addr = self.get_pfn(addrMsgEntry)
            if msgfun_addr < self.cmin or msgfun_addr > self.cmax:
                return 0

            addrMsgEntry = addrMsgEntry + self.MSGStructSize

        return 0

    @staticmethod
    def MakeOffset(addr):
        if idc.__EA64__:
            idc.create_data(addr, idc.FF_0OFF | idc.FF_REF | idc.FF_QWORD, 8, idc.BADADDR)
        else:
            idc.create_data(addr, idc.FF_0OFF | idc.FF_REF | idc.FF_DWORD, 4, idc.BADADDR)

    def MakeAfxMSG(self, addr):
        if idc.__EA64__:
            self.MakeOffset(addr)
            self.MakeOffset(addr + 8)
        else:
            self.MakeOffset(addr)
            self.MakeOffset(addr + 4)

    def MakeMSG_ENTRY(self, addr):
        msgmapSize = 0
        addrGetThisMessageMap = self.getAword(addr, 0)
        addrMsgEntry = self.getAword(addr, 1)

        self.MakeAfxMSG(addr)
        if idc.get_name(addr) == ("off_%lX" % (addr)) or idc.get_name(addr) == "":
            idc.set_name(addr, "msgEntries_%lX" % (addr))

        pEntry = addrMsgEntry
        while idaapi.get_dword(pEntry) != 0:
            idc.MakeUnknown(pEntry, self.MSGStructSize, idc.DELIT_SIMPLE)
            if idc.MakeStructEx(pEntry, self.MSGStructSize, "AFX_MSGMAP_ENTRY") == 0:
                print("Create AFX_MSGMAP_ENTRY failed at %X" % pEntry)
                return 0

            msgName = self.GetMsgName(idc.Dword(pEntry + 0))

            str_funcmt  = "MSG function: " + msgName + "\n"
            str_funcmt += "    nMessage: " + ("0x%LX" % idc.Dword(pEntry + 0)) + "\n"
            str_funcmt += "       nCode: " + str(idc.Dword(pEntry + 4)) + "\n"
            str_funcmt += "         nID: " + str(idc.Dword(pEntry + 8)) + " - " + str(idc.Dword(pEntry + 12))

            func_startEa = self.get_pfn(pEntry)
            pfn = idaapi.get_func(func_startEa)
            if pfn is None:
                idc.MakeUnkn(func_startEa, idc.DELIT_SIMPLE)
                idaapi.add_func(func_startEa)
                pfn = idaapi.get_func(func_startEa)

            idaapi.set_func_cmt(pfn, str_funcmt, 0)
            oldname = idaapi.get_func_name(func_startEa)
            if oldname == "sub_%lX" % (func_startEa):
                newname = ""
                if idc.Dword(pEntry + 8) == idc.Dword(pEntry + 12):
                    if idc.Dword(pEntry + 8) != 0:
                        newname = "On_%s_%X_%u" % (msgName, func_startEa, idc.Dword(pEntry + 8))
                    else:
                        newname = "On_%s_%X" % (msgName, func_startEa)
                else:
                    newname = "On_%s_%X_%u_to_%u" % (msgName, func_startEa, idc.Dword(pEntry + 8), idc.Dword(pEntry + 12))

                idc.MakeName(func_startEa, newname)

            pEntry = pEntry + self.MSGStructSize

        # AFX_MSG_END
        idc.MakeUnknown(pEntry, self.MSGStructSize, idc.DELIT_SIMPLE)
        idc.MakeStructEx(pEntry, self.MSGStructSize, "AFX_MSGMAP_ENTRY")
        msgmapSize = pEntry - addrMsgEntry + self.MSGStructSize
        return msgmapSize

    # Search All AFX_MSGMAP
    def Search_MSGMAP(self):
        snum = ida_segment.get_segm_qty()

        for i in range(0, snum):
            s = ida_segment.getnseg(i)
            segname = ida_segment.get_segm_name(s)

            if segname == ".text":
                self.cmin = s.start_ea
                self.cmax = s.end_ea

            if segname == ".rdata":
                self.rmin = s.start_ea
                self.rmax = s.end_ea

        if self.cmin == self.cmax or self.cmax == 0:
            return 0
        if self.rmin == self.rmax or self.rmax == 0:
            return 0

        totalCount = 0
        parseCount = 0
        addr = self.rmin

        try:
            idaapi.show_wait_box("Search for AFX_MSGMAP...")
            values = list()
            while addr != idc.BADADDR:
                ret = self.CheckMSGMAP(addr)
                MSGMAPSize = 0
                if ret > 0:
                    totalCount += 1
                    strfind = "Find AFX_MSGMAP at 0x%X" % (addr)
                    idaapi.replace_wait_box(strfind)
                    print(strfind)

                    if idc.Name(addr) == "off_%lX" % (addr):
                        parseCount += 1

                    MSGMAPSize = self.MakeMSG_ENTRY(addr)

                    value = [
                        totalCount-1,
                        addr,
                        idc.Name(addr),
                        (MSGMAPSize - self.MSGStructSize) / self.MSGStructSize
                    ]
                    values.append(value)

                addr += MSGMAPSize + self.USize

                MSGMAPSize = 0
                if addr > self.rmax:
                    break
        finally:
            idaapi.hide_wait_box()

        c = AFXMSGMAPSearchResultChooser("Search AFX_MSGMAPs results", values)
        r = c.show()
        print("===== Search complete, total %lu, new resolution %lu=====\n" % (totalCount, parseCount))


class Kp_Menu_Context(idaapi.action_handler_t):
    @classmethod
    def get_name(self):
        return self.__name__

    @classmethod
    def get_label(self):
        return self.label

    @classmethod
    def register(self, plugin, label):
        self.plugin = plugin
        self.label = label
        instance = self()
        return idaapi.register_action(idaapi.action_desc_t(
            self.get_name(),  # Name. Acts as an ID. Must be unique.
            instance.get_label(),  # Label. That's what users see.
            instance  # Handler. Called when activated, and for updating
        ))

    @classmethod
    def unregister(self):
        """Unregister the action.
        After unregistering the class cannot be used.
        """
        idaapi.unregister_action(self.get_name())

    @classmethod
    def activate(self, ctx):
        # dummy method
        return 1

    @classmethod
    def update(self, ctx):
        try:
            if ctx.form_type == idaapi.BWN_DISASM:
                return idaapi.AST_ENABLE_FOR_FORM
            else:
                return idaapi.AST_DISABLE_FOR_FORM
        except:
            # Add exception for main menu on >= IDA 7.0
            return idaapi.AST_ENABLE_ALWAYS


# context menu for Patcher
class Kp_MC_Make_MSGMAP(Kp_Menu_Context):
    def activate(self, ctx):
        self.plugin.make_msgmap()
        return 1


# context menu for Fill Range
class Kp_MC_Find_MSGMAP(Kp_Menu_Context):
    def activate(self, ctx):
        self.plugin.search_msgmap()
        return 1


# hooks for popup menu
class Hooks(idaapi.UI_Hooks):
    # IDA >= 700 right click widget popup
    def finish_populating_widget_popup(self, form, popup):
        if idaapi.get_widget_type(form) == idaapi.BWN_DISASM:
            idaapi.attach_action_to_popup(form, popup, Kp_MC_Make_MSGMAP.get_name(), 'AFX_MSGMAP/')
            idaapi.attach_action_to_popup(form, popup, Kp_MC_Find_MSGMAP.get_name(), 'AFX_MSGMAP/')


class AfxMsgMapPlugin_t(idaapi.plugin_t):
    flags = idaapi.PLUGIN_UNL | idaapi.PLUGIN_HIDE
    comment = "AFX_MSGMAP identify"
    help = ""
    wanted_name = "AFX_MSGMAP Find"
    wanted_hotkey = ""

    def __init__(self):
        self.afxmsgmap = AfxMSGMap()

    def init(self):
        global plugin_initialized

        # register popup menu handlers
        Kp_MC_Make_MSGMAP.register(self, "Make as AFX_MSGMAP")
        Kp_MC_Find_MSGMAP.register(self, "Search AFX_MSGMAP")

        if not plugin_initialized:
            plugin_initialized = True
            idaapi.attach_action_to_menu("Search/AFX_MSGMAP/", Kp_MC_Make_MSGMAP.get_name(), idaapi.SETMENU_APP)
            idaapi.attach_action_to_menu("Search/AFX_MSGMAP/", Kp_MC_Find_MSGMAP.get_name(), idaapi.SETMENU_APP)

        # setup popup menu
        self.hooks = Hooks()
        self.hooks.hook()
        self.afxmsgmap.AddMSGMAPStruct()

        if idaapi.init_hexrays_plugin():
            addon = idaapi.addon_info_t()
            addon.id = "snow.afxmsgmap"
            addon.name = "AfxMSGMap"
            addon.producer = "Snow & HTC (VinCSS)"
            addon.url = ""
            addon.version = "7.00"
            idaapi.register_addon(addon)

            print("%s plugin installed - Written by snow<85703533> & HTC (VinCSS)" % self.wanted_name)

            return idaapi.PLUGIN_KEEP

        return idaapi.PLUGIN_SKIP

    def run(self, arg=0):
        return

    def term(self):
        if self.hooks is not None:
            self.hooks.unhook()
            self.hooks = None

        print("%s plugin terminated." % self.wanted_name)

    # null handler
    def make_msgmap(self):
        address = idc.get_screen_ea()
        if self.afxmsgmap.CheckMSGMAP(address) > 0:
            self.afxmsgmap.MakeMSG_ENTRY(address)
        else:
            print("This is not a AFX_MSGMAP\n")

    # handler for About menu
    def search_msgmap(self):
        self.afxmsgmap.Search_MSGMAP()


def PLUGIN_ENTRY():
    return AfxMsgMapPlugin_t()
