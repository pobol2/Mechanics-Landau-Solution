// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// §11 Problem 1, simple pendulum: one point mass, gravity and a massless rod of
// fixed length from a fixed pivot at the origin, with no angle in the model.
// The engine's DistanceConstraint is bilateral (a rigid rod); a string is
// equivalent only while the rod is in tension.
//
// The engine frame has Y pointing up, gravity (0, -g, 0). phi = atan2(X, -Y) is
// measured from the downward vertical, as in §5 Problem 1. The particle is
// released at rest at phi = amplitude.
#include "study.hpp"

using Eigen::Vector3d;

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double l = o["length"], phi0 = o["amplitude"];
        if (l <= 0.0) throw std::invalid_argument("length must be positive");

        physics::Model model;
        model.masses = {o["mass"]};
        model.gravity = {0.0, -o["g"], 0.0};
        model.distance_constraints = {{0, Vector3d::Zero(), l}}; // pivot - mass

        physics::State state;
        state.positions = {l * Vector3d(std::sin(phi0), -std::cos(phi0), 0)};
        state.velocities = {Vector3d::Zero()};

        physics::Simulation sim(model, state);
        study::run(o, sim, {"phi", "dphi"}, [](const physics::State& s, double) {
            const Vector3d &q = s.positions[0], &v = s.velocities[0];
            const double x = q.x(), y = -q.y(), vx = v.x(), vy = -v.y();
            return std::vector<double>{std::atan2(x, y), (y * vx - x * vy) / (x * x + y * y)};
        });
    });
}
