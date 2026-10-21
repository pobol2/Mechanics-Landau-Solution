// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// §5 Problem 2, pendulum with a moving support: two point masses, gravity, m1
// held on the horizontal X axis by two planes (Y = 0 and Z = 0) and a massless
// rigid rod from m1 to m2, with no angle in the model.
//
// The engine frame has Y pointing up, gravity (0, -g, 0). The manual's figure
// has y pointing down, so x = X, y = -Y, and phi = atan2(x2 - x, y2) is
// measured from the downward vertical. The engine's potential m g Y is the
// manual's -m g y.
#include "study.hpp"

using Eigen::Vector3d;

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double l = o["l"], x = o["x"], phi = o["phi"];

        physics::Model model;
        model.masses = {o["m1"], o["m2"]};
        model.gravity = {0.0, -o["g"], 0.0};
        model.constraints = {physics::planeConstraint(0, Vector3d::Zero(), Vector3d::UnitY()),
                             physics::planeConstraint(0, Vector3d::Zero(), Vector3d::UnitZ())};
        model.links = {{0, 1, l}}; // m1 - m2

        const Vector3d r1(x, 0, 0);
        const Vector3d v1(o["dx"], 0, 0);
        const Vector3d r = l * Vector3d(std::sin(phi), -std::cos(phi), 0);
        const Vector3d v = o["dphi"] * l * Vector3d(std::cos(phi), std::sin(phi), 0);
        physics::State state;
        state.positions = {r1, r1 + r};
        state.velocities = {v1, v1 + v};

        physics::Simulation sim(model, state);
        study::run(o, sim, {"x", "phi", "dx", "dphi"}, [](const physics::State& s, double) {
            const auto &q = s.positions, &v = s.velocities;
            const double rx = q[1].x() - q[0].x(), ry = -(q[1].y() - q[0].y());
            const double vx = v[1].x() - v[0].x(), vy = -(v[1].y() - v[0].y());
            return std::vector<double>{q[0].x(), std::atan2(rx, ry), v[0].x(),
                                       (ry * vx - rx * vy) / (rx * rx + ry * ry)};
        });
    });
}
