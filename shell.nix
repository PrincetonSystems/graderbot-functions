{
  pkgs ? import <nixpkgs> {},
  snapfaasSha256 ? "sha256-ZPqCq5vCyp/ej2m+w5KdWaPSj32xfA3g9k/tqDPFcDs=",
  snapfaasRev ? "259ec6d4fcdca97851960a07fe1782a63b79a0a6",
  snapfaasSrc ? pkgs.fetchFromGitHub {
    owner = "princeton-sns";
    repo = "snapfaas";
    rev = snapfaasRev;
    sha256 = snapfaasSha256;
  },
  release ? false
}:

with pkgs;
let
  snapfaas = (import snapfaasSrc { inherit pkgs release; });
in mkShell {
  buildInputs = [ lkl snapfaas.snapfaas snapfaas.webhook lmdb gnumake e2fsprogs ];
  shellHook = ''
    # Mark variables which are modified or created for export.
    set -a
    source ${toString ./.env}
    set +a
  '';
}
