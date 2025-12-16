# Copilot Instructions for Shodh

## Project Overview

**Shodh** is a CUDA/GPU computing project (inferred from `.gitignore`). This repository is in early development stages with foundational setup in place.

## Key Technology Stack

- **CUDA/GPU Computing**: Project handles CUDA compilation artifacts (`.cu`, `.ptx`, `.cubin`, `.fatbin`)
- **Apache 2.0 License**: All contributions must comply with Apache License 2.0

## Development Conventions

### Code Organization
- Structure to be established as project develops
- Consider GPU-specific patterns for compute kernels vs host code separation

### Build & Compilation
- CUDA compilation likely required - build instructions to be documented as project matures
- GPU artifacts (`.ptx`, `.cubin`, `.fatbin`) should not be committed per `.gitignore`

### Testing & Validation
- Testing strategy to be documented
- Consider GPU-specific testing (device compatibility, memory management)

## Future Expansion Areas

As the codebase grows, expand these instructions to cover:
1. Project architecture and component boundaries
2. Data flow between host (CPU) and device (GPU) code
3. Memory management patterns specific to CUDA
4. Build/compilation workflow and commands
5. Testing procedures and CI/CD pipeline
6. Performance profiling and optimization guidelines
7. Documentation of any external dependencies

## Project Links

- **Repository**: https://github.com/iAbhyuday/shodh
- **License**: Apache 2.0 (see LICENSE file)
