# Reference: Graph transformations — modulus, reflections
# Style: clean Axes (tips=False, x/y_range ~[-5,6], x/y_length=8),
# Succession for sequential creates, Transform for graph morphing, minimal labels

from manim import *
import numpy as np


class Modulus(Scene):
    def construct(self):
        ax = Axes(
            x_range=[-5, 6, 1],
            y_range=[-5, 6, 1],
            x_length=10,
            y_length=8,
            tips=False,
        ).shift(DOWN)

        function = "$f(x)=||x|^2-2|x|-3|$"
        title = Title(function, include_underline=False)

        eq = Tex(r"$x^2-2x-3$").move_to([-3.2, 1.2, 0]).scale(0.75)
        eq1 = Tex(r"$|x|^2-2|x|-3$").move_to([-3.2, 1.2, 0]).scale(0.75)
        eq2 = Tex(r"$||x|^2-2|x|-3|$").move_to([-3.2, 1.2, 0]).scale(0.75)

        graph = ax.plot(lambda x: x**2 - 2*x - 3, x_range=(-4, 4, 0.001)).set_color(BLUE_D)
        graph1 = ax.plot(lambda x: abs(x)**2 - 2*abs(x) - 3, x_range=(-4, 4, 0.001))
        graph2 = ax.plot(lambda x: abs(abs(x)**2 - 2*abs(x) - 3), x_range=(-4, 4, 0.001))

        self.add(title, ax)
        self.wait(1/30)
        self.play(Create(graph), Write(eq), Flash(eq, color=WHITE, flash_radius=0.5))
        self.wait()
        self.play(Transform(graph, graph1), Transform(eq, eq1))
        self.wait()
        self.play(Transform(graph, graph2), Transform(eq1, eq2))
        self.wait(3)


class GraphTransformSplit(Scene):
    """Split left/right halves for |x| transformation."""
    def construct(self):
        ax = Axes(
            x_range=[-5, 6, 1],
            y_range=[-5, 6, 1],
            x_length=10,
            y_length=8,
            tips=False,
        ).shift(DOWN)

        function = "$f(x)=||x|^2-2|x|-3|$"
        title = Title(function, include_underline=False)

        eq = Tex(r"$x^2-2x-3$").move_to([-3.2, 1.2, 0]).scale(0.75)
        eq1 = Tex(r"$|x|^2-2|x|-3$").move_to([-3.2, 1.2, 0]).scale(0.75)
        eq2 = Tex(r"$||x|^2-2|x|-3|$").move_to([-3.2, 1.2, 0]).scale(0.75)

        def f1(x): return x**2 - 2*x - 3
        def f2(x): return abs(x)**2 - 2*abs(x) - 3
        def f3(x): return abs(abs(x)**2 - 2*abs(x) - 3)

        graph_left = ax.plot(f1, x_range=(-5, 0, 0.001))
        graph_right = ax.plot(f1, x_range=(0, 5, 0.001))
        graph_left_m = ax.plot(f2, x_range=(-5, 0, 0.001))
        graph_right_M = ax.plot(f3, x_range=(0, 5, 0.001))
        graph_left_M = ax.plot(f3, x_range=(-5, 0, 0.001))

        self.add(title, ax)
        self.wait(1/30)
        self.play(Create(graph_left), Create(graph_right), Write(eq),
                  Flash(eq, color=WHITE, flash_radius=0.5))
        self.wait()
        self.play(FadeOut(graph_left, shift=DOWN))
        self.play(FadeIn(graph_left_m, shift=LEFT), Transform(eq, eq1))
        self.play(Transform(graph_left_m, graph_left_M),
                  Transform(graph_right, graph_right_M),
                  Transform(eq1, eq2))
        self.wait()
