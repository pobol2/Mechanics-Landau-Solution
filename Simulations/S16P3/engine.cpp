// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// §16 Problem 3: disintegration of a particle moving with the velocity V along
// the engine X axis into two particles of masses m1 and m2. The two parts start
// at rest relative to each other, a distance R/2 apart along the emission
// direction (cos theta0, sin theta0, 0) of particle 1, with their centre of mass
// at the origin. They repel each other with the short-range potential
// U(r) = 16 epsilon (1 - r/R)^4 for r < R and U = 0 beyond, so that the energy
// released when they separate is the disintegration energy epsilon; the force
// and its first two derivatives are continuous at r = R. After separation both
// particles move freely.
#include "study.hpp"

#include "physics/force.hpp"

using Eigen::Vector3d;

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double m1 = o["mass1"], m2 = o["mass2"], epsilon = o["energy"], R = o["range"];
        const double V = o["speed"], theta0 = o["emission"];
        if (m1 <= 0.0 || m2 <= 0.0 || epsilon <= 0.0 || R <= 0.0)
            throw std::invalid_argument("the masses, the energy and the range must be positive");
        const double U0 = 16.0 * epsilon;

        physics::RadialPotential repulsion;
        repulsion.energy = [=](double r) { return r < R ? U0 * std::pow(1.0 - r / R, 4) : 0.0; };
        repulsion.derivative = [=](double r) { return r < R ? -4.0 * U0 / R * std::pow(1.0 - r / R, 3) : 0.0; };

        physics::Model model;
        model.masses = {m1, m2};
        model.forces = {physics::pairForce(0, 1, repulsion)};

        const double M = m1 + m2, r0 = R / 2;
        const Vector3d n(std::cos(theta0), std::sin(theta0), 0.0), velocity(V, 0.0, 0.0);
        physics::State state;
        state.positions = {m2 / M * r0 * n, -m1 / M * r0 * n};
        state.velocities = {velocity, velocity};

        physics::Simulation sim(model, state);
        study::run(o, sim, {"separation"}, [](const physics::State& s, double) {
            return std::vector<double>{(s.positions[0] - s.positions[1]).norm()};
        });
    });
}
