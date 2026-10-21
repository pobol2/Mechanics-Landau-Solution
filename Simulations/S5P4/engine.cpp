// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// §5 Problem 4, rotating system: three point masses and gravity. Each m1 hangs
// on a massless rigid rod from a fixed pivot and is linked to m2 by another; m2
// is held on the vertical axis by two fixed planes (X = 0 and Z = 0). The two
// m1 are held in a vertical plane through the axis that rotates at the
// constant angular velocity Omega, which imposes the rotation. No angle is in
// the model.
//
// The engine frame has Y pointing up the rotation axis, the pivot at the
// origin and gravity (0, -g, 0); the plane of the rods starts as Z = 0. The
// manual's theta is the angle of the upper rods from the downward axis,
// theta = atan2(rho, -Y) with rho the distance of m1 from the axis. The
// rotating plane does work, so E is not conserved but the Jacobi integral
// E - Omega M_Y is (M_Y the angular momentum about the axis).
#include "study.hpp"

#include <Eigen/Geometry>

using Eigen::Vector3d;

int main(int argc, char** argv) {
    return study::main(argc, argv, [](const study::Options& o) {
        const double m1 = o["m1"], m2 = o["m2"], a = o["a"], g = o["g"], omega = o["Omega"];
        const double theta = o["theta"], dtheta = o["dtheta"];
        const Vector3d rotation(0, omega, 0);

        physics::Model model;
        model.masses = {m1, m1, m2};
        model.gravity = {0.0, -g, 0.0};
        model.distance_constraints = {{0, Vector3d::Zero(), a}, {1, Vector3d::Zero(), a}}; // pivot - m1
        model.links = {{0, 2, a}, {1, 2, a}};                                              // m1 - m2
        model.constraints = {physics::planeConstraint(0, Vector3d::Zero(), Vector3d::UnitZ(), rotation),
                             physics::planeConstraint(1, Vector3d::Zero(), Vector3d::UnitZ(), rotation),
                             physics::planeConstraint(2, Vector3d::Zero(), Vector3d::UnitX()),
                             physics::planeConstraint(2, Vector3d::Zero(), Vector3d::UnitZ())};

        // Velocities: the motion in the plane, plus the plane's rotation Omega x r
        const double s = std::sin(theta), c = std::cos(theta);
        const Vector3d r1(a * s, -a * c, 0), r2(-a * s, -a * c, 0);
        physics::State state;
        state.positions = {r1, r2, {0, -2 * a * c, 0}};
        state.velocities = {dtheta * a * Vector3d(c, s, 0) + rotation.cross(r1),
                            dtheta * a * Vector3d(-c, s, 0) + rotation.cross(r2), {0, 2 * a * s * dtheta, 0}};

        physics::Simulation sim(model, state);
        study::run(o, sim, {"theta", "dtheta", "jacobi"}, [=](const physics::State& st, double) {
            const auto &q = st.positions, &v = st.velocities;
            const double rho = std::hypot(q[0].x(), q[0].z()), y = -q[0].y();
            const double drho = (q[0].x() * v[0].x() + q[0].z() * v[0].z()) / rho, dy = -v[0].y();
            double jacobi = 0;
            for (std::size_t i = 0; i < q.size(); ++i) {
                const double m = i < 2 ? m1 : m2;
                jacobi += m * (0.5 * v[i].squaredNorm() + g * q[i].y() - omega * q[i].cross(v[i]).y());
            }
            return std::vector<double>{std::atan2(rho, y), (y * drho - rho * dy) / (rho * rho + y * y), jacobi};
        });
    });
}
