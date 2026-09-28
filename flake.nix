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
