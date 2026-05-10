class Utask < Formula
  desc "UniversalTask (utask) v2.0 - Headless Task Sync CLI"
  homepage "https://github.com/aeon022/utask"
  url "https://github.com/aeon022/utask/releases/download/v2.0.0/utask-macos"
  sha256 "REPLACE_WITH_ACTUAL_SHA256" # Generiert via 'shasum -a 256 utask'
  version "2.0.0"

  def install
    bin.install "utask-macos" => "utask"
  end

  service do
    run [opt_bin/"utask", "daemon"]
    keep_alive true
    log_path var/"log/utaskd.log"
    error_log_path var/"log/utaskd.err.log"
  end

  test do
    system "#{bin}/utask", "--help"
  end
end
