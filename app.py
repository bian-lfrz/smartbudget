from textual.app import App
from auth import LoginScreen


class SmartBudgetApp(App):
    TITLE = "SmartBudget CLI"
    SUB_TITLE = "Pengelola Keuangan Bulanan Mahasiswa"
    CSS_PATH = "style.tcss"

    def on_mount(self):
        self.dark = True
        self.push_screen(LoginScreen())


if __name__ == "__main__":
    SmartBudgetApp().run()