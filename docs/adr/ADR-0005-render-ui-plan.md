# ADR-0005 Visual modernization is a renderer + art + UI problem
Status: Proposed (decide at B3 start with measurements)
**Context.** WW3D2/DX8-era renderer. Higher-resolution textures alone do not deliver modern lighting, materials or UI scaling.
**Plan.** Measure on client hardware: frame time with 4x textures; feasibility of a post-process pass (tonemap/AO/bloom) inside the W3D device layer; UI layout scaling at 1080p/1440p/4K. Output: options with cost and evidence (stay-and-extend vs. new backend). Engine-direction change requires client approval.
