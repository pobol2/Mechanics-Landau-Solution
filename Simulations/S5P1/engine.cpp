// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// §5 Problem 1, coplanar double pendulum: two point masses, gravity, a fixed
// pivot and two massless rigid rods, with no angles in the model.
//
// The engine frame has Y pointing up, gravity (0, -g, 0). The manual's figure
// has y pointing down, so x = X, y = -Y, and phi = atan2(x, y) is measured from
// the downward vertical. The engine's potential m g Y is the manual's -m g y.
#include "study.hpp"

using Eigen::Vector3d;

// Angle of a rod from the downward vertical and its rate, from its end points
static void angle(const Vector3d& from, const Vector3d& to, const Vector3d& v_from, const Vector3d& v_to,
                  std::vector<double>& angles, std::vector<double>& rates) {
    const double x = to.x() - from.x(), y = -(to.y() - from.y());
    const double vx = v_to.x() - v_from.x(), vy = -(v_to.y() - v_from.y());
    angles.push_back(std::atan2(x, y));
    rates.push_back((y * vx - x * vy) / (x * x + y * y));
}

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double l1 = o["l1"], l2 = o["l2"], phi1 = o["phi1"], phi2 = o["phi2"];

        physics::Model model;
        model.masses = {o["m1"], o["m2"]};
        model.gravity = {0.0, -o["g"], 0.0};
        model.distance_constraints = {{0, Vector3d::Zero(), l1}}; // pivot - m1
        model.links = {{0, 1, l2}};                                 // m1 - m2

        const Vector3d r1 = l1 * Vector3d(std::sin(phi1), -std::cos(phi1), 0);
        const Vector3d r2 = l2 * Vector3d(std::sin(phi2), -std::cos(phi2), 0);
        const Vector3d v1 = o["dphi1"] * l1 * Vector3d(std::cos(phi1), std::sin(phi1), 0);
        const Vector3d v2 = o["dphi2"] * l2 * Vector3d(std::cos(phi2), std::sin(phi2), 0);
        physics::State state;
        state.positions = {r1, r1 + r2};
        state.velocities = {v1, v1 + v2};

        physics::Simulation sim(model, state);
        study::run(o, sim, {"phi1", "phi2", "dphi1", "dphi2"}, [](const physics::State& s, double) {
            const auto &q = s.positions, &v = s.velocities;
            std::vector<double> angles, rates;
            angle(Vector3d::Zero(), q[0], Vector3d::Zero(), v[0], angles, rates);
            angle(q[0], q[1], v[0], v[1], angles, rates);
            angles.insert(angles.end(), rates.begin(), rates.end());
            return angles;
        });
    });
}
