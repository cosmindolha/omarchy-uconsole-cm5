# Hardware fixes and maintenance

These are observations from the working CM5 unit on 2026-09-05. A successful build or fixture is not a substitute for checking another physical device.

## Display and input

The 5-inch panel is physically landscape 1280×720, while DRM exposes native 720×1280. Hyprland transform **3** produces the upright orientation on this unit. The toolkit uses scale **1.25**, yielding 1024×576 logical space, with shell text 20 px and terminal text 15 pt. SDDM gets its own rotated compositor configuration.

The keyboard exposes separate ordinary keyboard, consumer-control and mouse devices. Match their observed names instead of `/dev/input/eventN`, whose numbering can change. The mouse gets `/dev/input/uconsole-mouse`; the evdev helper preserves motion and maps the trackball's middle-click event to left click.

The toolkit maps onboard Right Alt to Super and supplies Left Alt alternatives. The speaker key's held volume-down event becomes Mod3 on its consumer-control interface. Mod3+Up/Down adjusts volume, including held repeats. The firmware's Fn+speaker mute stays available. This was verified through the real input devices and PipeWire volume changes; physical Alt shortcuts were confirmed by the user.

The backlight has integer levels **0–9**. The toolkit uses steps of one, keeps normal dimming above zero, and gives the video group write access through udev. Firmware Fn+Space controls keyboard lighting.

## Audio

GPIO10 detects the headphone jack; low enables the speaker amplifier through GPIO11, high disables it. `audio_3.5_patch.py` reads the actual pin level and updates the amplifier. The shutdown service lowers GPIO11. This preserves the routing behavior of the working vendor installation. Headphone insertion still needs checking on each hardware revision.

## Power and battery

The kernel exposes `axp20x-battery` and `axp22x-ac`. The tested unit's fuel gauge reported 100% at roughly 3.6 V while discharging. Direct read-only PMIC inspection found a charge counter above its configured full capacity; this is a gauge state problem, not simply a stale shell icon.

The toolkit shows voltage and current and computes battery power as `abs(voltage × current)`. It labels the percentage unreliable after detecting the contradiction. The driver's `power_now` was zero despite real current, so that field is not used. Charging was independently verified from external power online, status Charging and roughly +1.98 A into the cells. Adapter label wattage is not measured battery charging power.

See [battery diagnosis](https://github.com/cosmindolha/omarchy-uconsole-clear-theme/blob/main/docs/BATTERY.md). No capacity estimate is fabricated, no PMIC registers are written by the toolkit, and fuel-gauge calibration has not been completed. The current setting is 6700 mAh total; check the capacity of the installed cells before changing it.

The panel is an IPS LCD. A darker theme improves contrast but does not switch off its backlight pixels. Reducing backlight brightness is the direct display power control. One-hour idle locking was chosen for active testing, not minimum power consumption. It can be shortened in `~/.config/omarchy/shell.json` later.

## Kernel, packages and known limits

`linux-uconsole-cm5` registers the carried-forward kernel and matching device trees in pacman. It has no automatic upstream build channel. Update kernel, modules, firmware and overlays as a matched, tested set; do not replace them with generic `linux-aarch64` or U-Boot packages.

The preserved kernel lacks Landlock. `DisableSandboxFilesystem` avoids pacman failing to create its filesystem sandbox; package signatures and syscall sandboxing remain enabled. The toolkit installs a pre-refresh hook to retain that setting. This is a compatibility concession to the vendor kernel.

The RC1's unavailable ttfx screensaver is disabled. Native locking and display blanking work. Suspend/resume, battery runtime, a complete gauge learning cycle, CM4 support, and a fresh generalized installation on a second device have not been validated. Omarchy applications with x86-only dependencies need their own ARM alternatives.

Upstream references: [ClockworkPi hardware/firmware](https://github.com/clockworkpi/uConsole), [CM5 vendor kernel](https://github.com/ak-rex/ClockworkPi-linux/tree/rpi-6.12.y), [Omarchy 4 Pi RC1](https://github.com/pkyanam/omarchy-4-pi/releases/tag/v0.1.0-rc.1).
