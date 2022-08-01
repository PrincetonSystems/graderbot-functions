{
  pkgs ? import <nixpkgs> {},
  release ? false
}:

with pkgs;
let
  snapfaasSrc = ../snapfaas;
  snapfaas = (import snapfaasSrc { inherit pkgs release; }).snapfaas;
in mkShell {
  buildInputs = [ lkl snapfaas lmdb gnumake e2fsprogs ];
  shellHook = ''
    # Mark variables which are modified or created for export.
    set -a
    source ${toString ./.env}
    set +a
  '';
}
