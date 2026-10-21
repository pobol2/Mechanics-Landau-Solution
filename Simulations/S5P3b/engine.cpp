// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// §5 Problem 3(b), support oscillating horizontally: one point mass, gravity
// and a massless rigid rod from a support that oscillates along X as
// a cos(gamma t), with no angle in the model.
//
// The engine frame has Y pointing up, gravity (0, -g, 0). The manual's figure
// has y pointing down, so x = X, y = -Y, and phi = atan2(x - x_s, y - y_s) is
// measured from the downward vertical through the support s.
#include "study.hpp"

using Eigen::Vector3d;

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double l = o["l"], phi = o["phi"];
        const physics::Motion support = physics::Motion::oscillating(Vector3d::Zero(), {o["a"], 0, 0}, o["gamma"]);

        physics::Model model;
        model.masses = {o["m"]};
        model.gravity = {0.0, -o["g"], 0.0};
        model.distance_constraints = {{0, support, l}}; // support - m

        physics::State state;
        state.positions = {support.position(0) + l * Vector3d(std::sin(phi), -std::cos(phi), 0)};
        state.velocities = {support.velocity(0) + o["dphi"] * l * Vector3d(std::cos(phi), std::sin(phi), 0)};

        physics::Simulation sim(model, state);
        study::run(o, sim, {"phi", "dphi"}, [support](const physics::State& s, double t) {
            const Vector3d r = s.positions[0] - support.position(t), v = s.velocities[0] - support.velocity(t);
            const double x = r.x(), y = -r.y(), vx = v.x(), vy = -v.y();
            return std::vector<double>{std::atan2(x, y), (y * vx - x * vy) / (x * x + y * y)};
        });
    });
}
