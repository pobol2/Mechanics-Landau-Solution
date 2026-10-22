// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// §11 Problem 2(a): one particle of mass m moving along the engine X axis in
// the potential U = A|X|^n, with the force F_X = -A n |X|^(n-1) sign(X). The
// potential is used as stated, without smoothing at X = 0. The particle is
// released at rest from the turning point X = (E/A)^(1/n), so that its energy
// is E.
#include "study.hpp"

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double A = o["A"], n = o["n"], E = o["energy"];
        if (A <= 0.0 || n <= 0.0 || E <= 0.0)
            throw std::invalid_argument("A, n and the energy must be positive");
        physics::CustomForce well;
        well.particles = {0};
        well.apply = [=](const physics::SystemView& s, physics::Vectors& f) {
            const double x = s.state.positions[0].x();
            const double sign = (x > 0.0) - (x < 0.0);
            f[0].x() -= A * n * std::pow(std::abs(x), n - 1.0) * sign;
        };
        well.potential = [=](const physics::SystemView& s) {
            return A * std::pow(std::abs(s.state.positions[0].x()), n);
        };
        physics::Model model;
        model.masses = {o["mass"]};
        model.forces = {physics::customForce(well)};
        physics::State state;
        state.positions = {{std::pow(E / A, 1.0 / n), 0.0, 0.0}};
        state.velocities = {{0.0, 0.0, 0.0}};
        physics::Simulation sim(model, state);
        study::run(o, sim, {}, [](const physics::State&, double) { return std::vector<double>{}; });
    });
}
