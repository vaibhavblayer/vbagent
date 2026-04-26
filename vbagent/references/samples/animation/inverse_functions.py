# Reference: Inverse function graphs — f(x) and f^{-1}(x) with y=x line
# Style: clean Axes (tips=False, x/y_length=9), Succession for sequential creates,
# get_graph_label for labels, y=x as thin gray reference line

from manim import *
import numpy as np


class CosInverse(Scene):
    def construct(self):
        ax = Axes(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            x_length=9,
            y_length=9,
            tips=False,
        )

        cos_graph = ax.plot(lambda x: np.cos(x), x_range=(0, PI, 0.001))
        arccos_graph = ax.plot(lambda x: np.arccos(x), x_range=(-1, 1, 0.001))
        identity = ax.plot(lambda x: x, x_range=(-4, 4, 0.001),
                           color=GRAY_B, stroke_width=1)

        cos_label = ax.get_graph_label(cos_graph, r"\cos(x)", x_val=3, direction=UP)
        arccos_label = ax.get_graph_label(cos_graph, r"\cos^{-1}(x)",
                                          x_val=-1, direction=20*UP)

        self.add(ax)
        self.play(Succession(Create(cos_graph), Write(cos_label)), run_time=3)
        self.play(Create(identity))
        self.play(Succession(Create(arccos_graph), Write(arccos_label)), run_time=3)
        self.wait(3)


class SinInverse(Scene):
    def construct(self):
        ax = Axes(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            x_length=9,
            y_length=9,
            tips=False,
        )

        sin_graph = ax.plot(lambda x: np.sin(x), x_range=(-PI/2, PI/2, 0.001))
        arcsin_graph = ax.plot(lambda x: np.arcsin(x), x_range=(-1, 1, 0.001),
                               color=BLUE_B)
        identity = ax.plot(lambda x: x, x_range=(-4, 4, 0.001),
                           color=GRAY_B, stroke_width=1)

        sin_label = ax.get_graph_label(sin_graph, r"\sin(x)",
                                       x_val=PI/2, direction=UP)
        arcsin_label = ax.get_graph_label(sin_graph, r"\sin^{-1}(x)",
                                          x_val=1, direction=10*UP)

        self.add(ax)
        self.play(Succession(Create(sin_graph), Write(sin_label)), run_time=3)
        self.play(Create(identity))
        self.play(Succession(Create(arcsin_graph), Write(arcsin_label)), run_time=3)
        self.wait(3)


class CubicAndInverse(Scene):
    def construct(self):
        ax = Axes(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            x_length=9,
            y_length=9,
            tips=False,
        )

        x3 = ax.plot(lambda x: x**3, x_range=(-1.7, 1.7, 0.001))

        def fx13(x):
            return x**(1/3) if x >= 0 else -(-x)**(1/3)

        x13 = ax.plot(fx13, x_range=(-4, 4, 0.001))
        identity = ax.plot(lambda x: x, x_range=(-4, 4, 0.001),
                           color=GRAY_B, stroke_width=1)

        x3_label = ax.get_graph_label(x3, "x^3", x_val=1.25, direction=UP)
        x13_label = ax.get_graph_label(x3, "x^{1/3}", x_val=1.5, direction=21*DOWN)

        self.add(ax)
        self.play(Succession(Create(x3), Write(x3_label)), run_time=3)
        self.play(Create(identity))
        self.play(Succession(Create(x13), Write(x13_label)), run_time=3)
        self.wait(3)
