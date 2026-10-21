// SPDX-License-Identifier: MIT
// Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
//
// Shared helpers of the engine side of a study: reading the options passed by
// study.py and writing the samples to a CSV file. Each problem's engine.cpp
// builds its own Model and State and chooses the columns it reports.
#pragma once

#include "physics/simulation.hpp"

#include <cmath>
#include <exception>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace study {

// Options given as --name value; every value but --csv is a number.
class Options {
public:
    Options(int argc, char** argv) {
        for (int i = 1; i + 1 < argc; i += 2) {
            const std::string key = argv[i];
            if (key.rfind("--", 0) != 0) throw std::invalid_argument("expected --name value, got " + key);
            if (key == "--csv") csv = argv[i + 1];
            else values_[key.substr(2)] = std::stod(argv[i + 1]);
        }
        if (argc % 2 == 0) throw std::invalid_argument("expected --name value pairs");
    }
    double operator[](const std::string& name) const {
        const auto it = values_.find(name);
        if (it == values_.end()) throw std::invalid_argument("missing --" + name);
        return it->second;
    }
    std::string csv;

private:
    std::map<std::string, double> values_;
};

// Advances `sim` to --duration with adaptive steps (--tolerance), and writes a
// row every --dt: the time, the given columns, each particle's position and
// velocity in the engine frame (X1, Y1, Z1, VX1, ..., numbered from 1), then
// the engine's linear momentum, energy, scaled energy-balance error (energy
// change minus external work, see physics::Diagnostics) and constraint
// residuals. The sampler gets the state and the time (for a moving support).
using Sampler = std::function<std::vector<double>(const physics::State&, double time)>;
inline void run(const Options& options, physics::Simulation& sim, const std::vector<std::string>& columns,
                const Sampler& sample) {
    std::ofstream out(options.csv);
    if (!out) throw std::runtime_error("cannot open " + options.csv);
    out.precision(17);
    out << "t";
    for (const auto& c : columns) out << ',' << c;
    for (std::size_t i = 1; i <= sim.state().positions.size(); ++i)
        for (const char* c : {"X", "Y", "Z", "VX", "VY", "VZ"}) out << ',' << c << i;
    out << ",momentum_X,momentum_Y,momentum_Z,energy,energy_balance_error,constraint_error,"
           "constraint_velocity_error\n";

    physics::AdaptiveSettings settings;
    settings.relative_tolerance = settings.absolute_tolerance = options["tolerance"];
    const double duration = options["duration"];
    const long samples = std::lround(duration / options["dt"]);
    for (long k = 0; k <= samples; ++k) {
        if (k > 0) sim.advanceAdaptive(k == samples ? duration : duration * k / samples, settings);
        const physics::Diagnostics d = sim.diagnostics();
        out << sim.time();
        for (double value : sample(sim.state(), sim.time())) out << ',' << value;
        const auto& q = sim.state().positions;
        const auto& v = sim.state().velocities;
        for (std::size_t i = 0; i < q.size(); ++i)
            out << ',' << q[i].x() << ',' << q[i].y() << ',' << q[i].z() << ',' << v[i].x() << ',' << v[i].y()
                << ',' << v[i].z();
        const Eigen::Vector3d& p = d.momentum.linear;
        out << ',' << p.x() << ',' << p.y() << ',' << p.z() << ',' << d.energy.total() << ','
            << d.scaled_energy_balance_error << ',' << d.constraints.max_position_error << ',' << d.constraints.max_velocity_error << '\n';
    }
    if (!out) throw std::runtime_error("failed writing " + options.csv);
}

// Runs a study's main body and reports errors.
inline int main(int argc, char** argv, const std::function<void(const Options&)>& body) {
    try {
        body(Options(argc, argv));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}
} // namespace study
