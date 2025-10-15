# Shine Stacker

## Focus Stacking Processing Framework and GUI

An open-source, cross-platform tool for professional-quality focus stacking — from batch workflows to pixel-level retouching.

[![CI multiplatform](https://github.com/lucalista/shinestacker/actions/workflows/ci-multiplatform.yml/badge.svg)](https://github.com/lucalista/shinestacker/actions/workflows/ci-multiplatform.yml)
[![PyPI version](https://img.shields.io/pypi/v/shinestacker?color=success)](https://pypi.org/project/shinestacker/)
[![Python Versions](https://img.shields.io/pypi/pyversions/shinestacker)](https://pypi.org/project/shinestacker/)
[![Qt Versions](https://img.shields.io/badge/Qt-6-blue.svg?&logo=Qt&logoWidth=18&logoColor=white)](https://www.qt.io/qt-for-python)
[![pylint](https://img.shields.io/badge/PyLint-10.00-brightgreen?logo=python&logoColor=white)](https://github.com/lucalista/shinestacker/blob/main/.github/workflows/pylint.yml)
[![codecov](https://codecov.io/github/lucalista/shinestacker/graph/badge.svg?token=Y5NKW6VH5G)](https://codecov.io/github/lucalista/shinestacker)
[![Documentation Status](https://readthedocs.org/projects/shinestacker/badge/?version=latest)](https://shinestacker.readthedocs.io/en/latest/?badge=latest)
 [![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![PyPI Downloads](https://static.pepy.tech/badge/shinestacker)](https://pepy.tech/projects/shinestacker)


<center><img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/src/shinestacker/gui/ico/shinestacker.png' width="150" referrerpolicy="no-referrer" alt="Shine Stacker Logo"></center>

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies_stack.jpg' width="400" referrerpolicy="no-referrer">

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee_stack.jpg' width="400" referrerpolicy="no-referrer">

## Key Features
- 🚀 **Batch Processing**: Automatically align, balance, and stack hundreds of images — perfect for macro or microscopy datasets.
- 🧩 **Modular Architecture**: Combine configurable modules for alignment, normalization, and blending to build custom workflows.
- 🖌️ **Retouch Editor**: Interactively refine your stacked image by painting in details from individual frames.
- 📊 **Jupyter & Python Integration**: Use Shine Stacker as a library inside your Python or Jupyter workflows.
- 🪟 **Cross-Platform GUI**: Native app built with Qt6, available for Windows, macOS, and Linux.

## Interactive GUI

The graphical interface makes complex stacking tasks simple:
- **Project View** – Configure, preview, and run stacking workflows with optional intermediate results.
- **Retouch View** – Manually refine the final image by blending details from selected frames and applying filters.

Ideal for users who want the power of scripting and the comfort of a modern UI.

## Resources

 🌍 [Website on WordPress](https://shinestacker.wordpress.com) • 📖 [Main documentation](https://shinestacker.readthedocs.io) • 📝 [Changelog](https://github.com/lucalista/shinestacker/blob/main/CHANGELOG.md) 

## Note for macOS users

**The following note is only relevant if you download the application as compressed archive from the [release page](https://github.com/lucalista/shinestacker/releases).**

macOS system security prevents running applications downloaded from the web that come from developers that don't hold an Apple Developer Certificate. 

In order to prevent this, follow the instructions below:

1. Download the installer image ```shinestacker-macos.dmg```.
2. Double-click the image and copy the app into the Application folder.
3. Open a terminal (*Applications > Utilities > Terminal*)
4. Type the folliwng command on the terminal:
```bash
xattr -cr /Applications/shinestacker/shinestacker.app
```
5. Now you can double-click the Sine Stacker icon app and it should run.

macOS adds a quarantine flag to all files downloaded from the internet. The above command removes that flag while preserving all other application functionality.

## Acknowledgements & References

The first version of the core focus stack algorithm was initially inspired by the [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar that was used under permission of the author. The implementation in the latest releases was rewritten from the original code.

Key references:
* [Pyramid Methods in Image Processing](https://www.researchgate.net/publication/246727904_Pyramid_Methods_in_Image_Processing), E. H. Adelson, C. H. Anderson,  J. R. Bergen, P. J. Burt, J. M. Ogden, RCA Engineer, 29-6, Nov/Dec 1984
Pyramid methods in image processing
* [A Multi-focus Image Fusion Method Based on Laplacian Pyramid](http://www.jcomputers.us/vol6/jcp0612-07.pdf), Wencheng Wang, Faliang Chang, Journal of Computers 6 (12), 2559, December 2011

## License

<img src="https://www.gnu.org/graphics/lgplv3-147x51.png" alt="LGPL 3 logo">

- **Code**: The software is provided as is under the [GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.en.html). See [LICENSE](https://github.com/lucalista/shinestacker/blob/main/LICENSE) for details.
<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/src/shinestacker/gui/ico/shinestacker.png' width="150" referrerpolicy="no-referrer" alt="Shine Stacker Logo">

- **Logo**: The Shine Stacker logo was designed by [Alessandro Lista](https://linktr.ee/alelista). Copyright © Alessandro Lista. All rights reserved. The logo is not covered by the LGPL-3.0 license of this project.

## Attribution request
📸 If you publish images created with Shine Stacker, please consider adding a note such as:

*Created with Shine Stacker – https://github.com/lucalista/shinestacker*

This is not mandatory, but highly appreciated.

⭐ If you find Shine Stacker useful, consider starring the repo or sharing your results!  
Feedback and contributions are always welcome.

