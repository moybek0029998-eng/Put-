from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.utils import platform

ir = None
if platform == "android":
    from jnius import autoclass
    Context = autoclass("android.content.Context")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    ir = PythonActivity.mActivity.getSystemService(Context.CONSUMER_IR_SERVICE)


# ---------- IR protokollar (mikrosekundlarda) ----------
def bits_lsb(value, n):
    return [(value >> i) & 1 for i in range(n)]


def nec_like(header, addr_bytes, cmd, one_space=1690, zero_space=560, mark=560):
    p = list(header)
    data = addr_bytes + [cmd, (~cmd) & 0xFF]
    for byte in data:
        for b in bits_lsb(byte, 8):
            p += [mark, one_space if b else zero_space]
    p.append(mark)
    return 38000, p


def samsung(cmd):
    return nec_like([4500, 4500], [0x07, 0x07], cmd)


def lg(cmd):
    return nec_like([9000, 4500], [0x04, 0xFB], cmd)


def sony(cmd):
    p = [2400, 600]
    for b in bits_lsb(cmd, 7) + bits_lsb(1, 5):  # 7 bit buyruq + 5 bit manzil (TV=1)
        p += [1200 if b else 600, 600]
    return 40000, p


BRANDS = {
    "Samsung": (samsung, {"POWER": 0x02, "VOL+": 0x07, "VOL-": 0x0B,
                          "MUTE": 0x0F, "CH+": 0x48, "CH-": 0x4C, "SOURCE": 0x01}),
    "LG": (lg, {"POWER": 0x08, "VOL+": 0x02, "VOL-": 0x03,
                "MUTE": 0x09, "CH+": 0x00, "CH-": 0x01, "SOURCE": 0x0B}),
    "Sony": (sony, {"POWER": 0x15, "VOL+": 0x12, "VOL-": 0x13,
                    "MUTE": 0x14, "CH+": 0x10, "CH-": 0x11, "SOURCE": 0x25}),
}


class Remote(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=10, spacing=10, **kw)
        self.brand = Spinner(text="Samsung", values=list(BRANDS),
                             size_hint_y=None, height=120, font_size=36)
        self.add_widget(self.brand)
        self.status = Label(text="Tayyor", size_hint_y=None, height=60, font_size=28)
        self.add_widget(self.status)
        grid = GridLayout(cols=2, spacing=10)
        for name in ["POWER", "SOURCE", "VOL+", "CH+", "VOL-", "CH-", "MUTE"]:
            grid.add_widget(Button(text=name, font_size=40,
                                   on_release=lambda b: self.send(b.text)))
        self.add_widget(grid)

    def send(self, key):
        builder, keys = BRANDS[self.brand.text]
        freq, pattern = builder(keys[key])
        if ir is None:
            self.status.text = "Faqat telefonda ishlaydi"
        elif not ir.hasIrEmitter():
            self.status.text = "Telefonda IR port yo'q"
        else:
            ir.transmit(freq, pattern)
            if self.brand.text == "Sony":  # Sony 3 marta takrorlanadi
                ir.transmit(freq, pattern)
                ir.transmit(freq, pattern)
            self.status.text = f"{self.brand.text}: {key}"


class PultApp(App):
    def build(self):
        return Remote()


PultApp().run()
