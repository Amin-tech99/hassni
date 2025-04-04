{pkgs}: {
  deps = [
    pkgs.ffmpeg
    pkgs.pkg-config
    pkgs.postgresql
    pkgs.openssl
  ];
}
