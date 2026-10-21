// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
// Shared physical setup for the two mechanical-similarity experiments.
#pragma once
#include "study.hpp"

inline int anharmonicStudy(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double k = o["k"], alpha = o["alpha"], scale = o["scale"];
        if (k <= 0.0 || alpha <= 0.0 || scale <= 0.0)
            throw std::invalid_argument("positive potential coefficients required");
        physics::CustomForce oscillator;
        oscillator.particles = {0};
        oscillator.apply = [=](const physics::SystemView& s, physics::Vectors& f) {
            const double x = s.state.positions[0].x();
            f[0].x() -= scale * (k * x + alpha * x * x * x);
        };
        oscillator.potential = [=](const physics::SystemView& s) {
            const double x = s.state.positions[0].x();
            return scale * (k * x * x / 2.0 + alpha * std::pow(x, 4) / 4.0);
        };
        physics::Model model;
        model.masses = {o["mass"]};
        model.forces = {physics::customForce(oscillator)};
        physics::State state;
        state.positions = {{o["amplitude"], 0.0, 0.0}};
        state.velocities = {{0.0, 0.0, 0.0}};
        physics::Simulation sim(model, state);
        study::run(o, sim, {}, [](const physics::State&, double) { return std::vector<double>{}; });
    });
}
