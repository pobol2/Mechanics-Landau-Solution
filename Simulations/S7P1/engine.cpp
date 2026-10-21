// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
// Plane x=0; angles measured from +x, y lies in the interface.
#include "study.hpp"

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double width = o["width"], jump = o["jump"];
        if (width <= 0.0) throw std::invalid_argument("width must be positive");
        physics::CustomForce step;
        step.particles = {0};
        step.apply = [=](const physics::SystemView& s, physics::Vectors& f) {
            const double z = std::tanh(s.state.positions[0].x() / width);
            f[0].x() -= jump * (1.0 - z * z) / (2.0 * width);
        };
        step.potential = [=](const physics::SystemView& s) {
            return jump * (1.0 + std::tanh(s.state.positions[0].x() / width)) / 2.0;
        };
        physics::Model model;
        model.masses = {o["mass"]};
        model.forces = {physics::customForce(step)};
        physics::State state;
        state.positions = {{-1.0, 0.0, 0.0}};
        state.velocities = {{o["speed"] * std::cos(o["angle"]),
                             o["speed"] * std::sin(o["angle"]), 0.0}};
        physics::Simulation sim(model, state);
        study::run(o, sim, {}, [](const physics::State&, double) { return std::vector<double>{}; });
    });
}
