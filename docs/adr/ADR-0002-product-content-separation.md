# ADR-0002 Product/content separation and clean boot
Status: Accepted
**Decision.** Engine code in `engine/`; all product data in `pzh/` packed to our own `.big` archives. B1 runs privately on top of licensed EA archives in an isolated test copy and is labelled "prototype". B2 must boot a clean folder containing no EA archive.
**Mechanism.** B1: `-mod <abs path>\PZDev_B1.big` (override priority) + user `Maps\` folder. B2: `PZBase.big` (our replacements for every base-data file the engine needs) + `PZContent.big`; file-access log proves no EA file is opened.
**Never.** Copy any file out of the Steam install into `pzh/`; ship any EA-derived asset; modify the Steam install.
