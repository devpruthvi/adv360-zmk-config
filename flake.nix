{
  description = "ZMK firmware for the Kinesis Advantage 360 Pro";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

    zmk-nix = {
      url = "github:lilyinstarlight/zmk-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    zmk-nix,
  }: let
    forAllSystems = nixpkgs.lib.genAttrs (nixpkgs.lib.attrNames zmk-nix.packages);
  in {
    packages = forAllSystems (system: rec {
      default = firmware;

      # result/zmk_left.uf2 and result/zmk_right.uf2
      firmware = zmk-nix.legacyPackages.${system}.buildSplitKeyboard {
        name = "adv360pro";

        # Repo root is also a ZMK module (zephyr/module.yml, src/status_report.c)
        src = nixpkgs.lib.sourceFilesBySuffices self [".c" ".conf" ".keymap" ".txt" ".yml" "Kconfig"];

        board = "adv360pro_%PART%//zmk";

        enableZmkStudio = true;

        zephyrDepsHash = "sha256-/IO6K04ay3SdMbnekutDVvFUqIQPNMyEFFRIYU8rlsI=";

        meta = {
          description = "ZMK firmware for the Kinesis Advantage 360 Pro";
          license = nixpkgs.lib.licenses.mit;
          platforms = nixpkgs.lib.platforms.all;
        };
      };

      # Clears pairings and saved settings; flash to both halves before switching firmware
      settings-reset = zmk-nix.legacyPackages.${system}.buildSplitKeyboard {
        name = "adv360pro-settings-reset";
        src = nixpkgs.lib.fileset.toSource {
          root = ./.;
          fileset = ./config/west.yml;
        };
        board = "adv360pro_%PART%//zmk";
        shield = "settings_reset";
        inherit (firmware) westDeps;
        zephyrDepsHash = firmware.westDeps.outputHash;
      };

      adv360-status = nixpkgs.legacyPackages.${system}.writers.writePython3Bin "adv360-status" {
        libraries = [nixpkgs.legacyPackages.${system}.python3Packages.hidapi];
        flakeIgnore = ["E501" "W503"];
      } (builtins.readFile ./cli/adv360_status.py);

      # Regenerates keymap-drawer/adv360pro.{yaml,svg} from the keymap; run from the repo root
      draw = let
        pkgs = nixpkgs.legacyPackages.${system};
        deps = firmware.westDeps;
      in
        pkgs.writeShellApplication {
          name = "adv360-draw";
          runtimeInputs = [pkgs.keymap-drawer];
          text = ''
            if [ ! -f config/adv360pro.keymap ]; then
              echo "Run this from the root of adv360-zmk-config" >&2
              exit 1
            fi
            KEYMAP_zmk_additional_includes='["${deps}/modules/zmk/helpers/include"]' \
              keymap -c keymap-drawer/config.yaml parse -z config/adv360pro.keymap >keymap-drawer/adv360pro.yaml
            KEYMAP_zmk_additional_includes='["${deps}/zmk/app/dts", "${deps}/zmk/app/include"]' \
              keymap -c keymap-drawer/config.yaml draw keymap-drawer/adv360pro.yaml \
              -d ${deps}/zmk/app/boards/kinesis/adv360pro/adv360pro-layouts.dtsi >keymap-drawer/adv360pro.svg
            echo "Wrote keymap-drawer/adv360pro.yaml and keymap-drawer/adv360pro.svg"
          '';
        };

      # nix run .#flash [left|right]; flash-reset does the same with settings-reset
      flash = nixpkgs.legacyPackages.${system}.callPackage ./nix/flash.nix {
        inherit firmware;
        name = "adv360-flash";
      };
      flash-reset = nixpkgs.legacyPackages.${system}.callPackage ./nix/flash.nix {
        firmware = settings-reset;
        name = "adv360-flash-reset";
      };
      update = zmk-nix.packages.${system}.update;
    });

    devShells = forAllSystems (system: {
      default = zmk-nix.devShells.${system}.default;
    });
  };
}
