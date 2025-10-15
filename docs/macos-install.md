# Installation note for macOS users

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
