# Copies each half's .uf2 to its UF2 bootloader drive, on Linux and macOS.
# The drive is recognised by INFO_UF2.TXT, which every UF2 bootloader exposes.
{
  lib,
  stdenv,
  writeShellApplication,
  coreutils,
  gnugrep,
  gnused,
  util-linux,
  firmware,
  name,
}:
writeShellApplication {
  inherit name;
  runtimeInputs = [coreutils gnugrep gnused] ++ lib.optional stdenv.hostPlatform.isLinux util-linux;
  text = ''
    parts=("$@")
    if [ "''${#parts[@]}" -eq 0 ]; then
      parts=(left right)
    fi
    for part in "''${parts[@]}"; do
      if [ ! -f "${firmware}/zmk_$part.uf2" ]; then
        echo "Unknown half '$part' (expected left or right)" >&2
        exit 1
      fi
    done

    find_drive() {
      if [ "$(uname)" = Darwin ]; then
        for volume in /Volumes/*; do
          if [ -f "$volume/INFO_UF2.TXT" ]; then
            echo "$volume"
            return 0
          fi
        done
        return 1
      fi

      while read -r target; do
        if [ -f "$target/INFO_UF2.TXT" ]; then
          echo "$target"
          return 0
        fi
      done < <(findmnt -rno TARGET)

      # Not mounted yet: mount small removable FAT drives through udisks
      while read -r path fstype removable size mountpoint; do
        if [ "$removable" = 1 ] && [ "$fstype" = vfat ] && [ -z "$mountpoint" ] && [ "$size" -le 268435456 ]; then
          udisksctl mount --block-device "$path" >/dev/null 2>&1 || true
        fi
      done < <(lsblk -rbpno PATH,FSTYPE,RM,SIZE,MOUNTPOINT)
      return 1
    }

    for part in "''${parts[@]}"; do
      echo -n "Put the $part half into bootloader mode with its USB cable connected to this computer "
      until drive="$(find_drive)"; do
        echo -n .
        sleep 1
      done
      echo
      echo "Found bootloader drive at $drive"
      grep -E '^(Model|Board-ID):' "$drive/INFO_UF2.TXT" | sed 's/^/  /' || true

      # The half reboots as soon as the file lands, so the copy itself may report an I/O error
      if [ "$(uname)" = Darwin ]; then
        cp -X "${firmware}/zmk_$part.uf2" "$drive/" 2>/dev/null || true
      else
        cp "${firmware}/zmk_$part.uf2" "$drive/" 2>/dev/null || true
        sync
      fi

      for _ in $(seq 30); do
        [ -f "$drive/INFO_UF2.TXT" ] || break
        sleep 1
      done
      if [ -f "$drive/INFO_UF2.TXT" ]; then
        echo "The $part half did not reboot; the copy may have failed. Try again." >&2
        exit 1
      fi
      echo "Flashed the $part half."
    done
  '';
}
