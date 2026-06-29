from __future__ import annotations

import random
import sys
from pathlib import Path
from tkinter import Label, PhotoImage, Tk


ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "assets" / "frames"
TRANSPARENT_BG = "#00ff00"


class LibertyPet:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT_BG)
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT_BG)
        except Exception:
            try:
                self.root.configure(bg="systemTransparent")
                self.root.attributes("-transparent", True)
            except Exception:
                pass

        self.photos: dict[str, list[PhotoImage]] = {}
        for state in ("idle", "idle_left", "run", "run_left", "eat", "eat_left", "sleep", "sleep_left"):
            paths = sorted((FRAMES / state).glob("*.png"))
            if not paths:
                raise RuntimeError(f"No frames found for {state}")
            self.photos[state] = [PhotoImage(file=str(path)) for path in paths]

        first = self.photos["idle"][0]
        self.width = first.width()
        self.height = first.height()
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.x = max(20, self.screen_w // 2 - self.width // 2)
        self.y = max(40, self.screen_h - self.height - 90)
        self.direction = 1
        self.frame_index = 0
        self.state = "idle"
        self.state_ticks = 0
        self.drag_origin: tuple[int, int] | None = None

        self.label = Label(self.root, image=first, bd=0, bg=TRANSPARENT_BG, highlightthickness=0)
        self.label.pack()

        self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.drag)
        self.root.bind("<Double-Button-1>", lambda _event: self.set_state("eat", 34))
        self.root.bind("<Button-2>", lambda _event: self.close())
        self.root.bind("<Button-3>", lambda _event: self.close())
        self.root.bind("<KeyPress-q>", lambda _event: self.close())
        self.root.bind("<KeyPress-Escape>", lambda _event: self.close())

    def state_name(self) -> str:
        suffix = "_left" if self.direction < 0 else ""
        if self.state == "run":
            return "run_left" if self.direction < 0 else "run"
        if self.state == "eat":
            return "eat_left" if self.direction < 0 else "eat"
        if self.state == "sleep":
            return "sleep_left" if self.direction < 0 else "sleep"
        return "idle_left" if self.direction < 0 else "idle"

    def set_state(self, state: str, ticks: int | None = None) -> None:
        self.state = state
        self.frame_index = 0
        if ticks is None:
            ticks = {
                "idle": random.randint(15, 35),
                "run": random.randint(55, 120),
                "eat": random.randint(30, 46),
                "sleep": random.randint(45, 80),
            }[state]
        self.state_ticks = ticks

    def choose_next_state(self) -> None:
        roll = random.random()
        if roll < 0.58:
            self.set_state("run")
        elif roll < 0.82:
            self.set_state("idle")
        elif roll < 0.95:
            self.set_state("eat")
        else:
            self.set_state("sleep")

    def move_if_needed(self) -> None:
        if self.state != "run":
            return
        self.x += self.direction * 7
        left_edge = -self.width // 3
        right_edge = self.screen_w - self.width + self.width // 3
        if self.x <= left_edge:
            self.x = left_edge
            self.direction = 1
        elif self.x >= right_edge:
            self.x = right_edge
            self.direction = -1
        self.y += random.choice((-1, 0, 0, 1))
        self.y = min(max(20, self.y), self.screen_h - self.height - 35)

    def tick(self) -> None:
        state = self.state_name()
        frames = self.photos[state]
        image = frames[self.frame_index % len(frames)]
        self.label.configure(image=image)
        self.frame_index += 1
        self.move_if_needed()
        self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")

        self.state_ticks -= 1
        if self.state_ticks <= 0:
            self.choose_next_state()
        self.root.after(95, self.tick)

    def start_drag(self, event) -> None:
        self.drag_origin = (event.x, event.y)

    def drag(self, event) -> None:
        if self.drag_origin is None:
            return
        ox, oy = self.drag_origin
        self.x = self.root.winfo_pointerx() - ox
        self.y = self.root.winfo_pointery() - oy
        self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")

    def close(self) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.choose_next_state()
        self.root.after(80, self.tick)
        self.root.mainloop()


if __name__ == "__main__":
    try:
        LibertyPet().run()
    except Exception as exc:
        print(f"Liberty desktop pet failed: {exc}", file=sys.stderr)
        raise
