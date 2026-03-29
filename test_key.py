from textual.app import App
from textual.widgets import Label

class TestKeyApp(App):
    def compose(self):
        yield Label("Press any key to see its name...")

    def on_key(self, event):
        self.notify(f"Key: {event.key}")
        if event.key == "q":
            self.exit()

if __name__ == "__main__":
    app = TestKeyApp()
    app.run()
