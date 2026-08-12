# Homebrew formula — the no-warning macOS install path.
#
#   brew tap udaysrinu/statementlens https://github.com/udaysrinu/StatementLens
#   brew install statementlens
#
# Why this exists: Gatekeeper's warning is triggered by the `com.apple.quarantine` extended
# attribute, which BROWSERS set on downloads — not by the absence of a signature. Homebrew never sets
# it, so a formula install launches with no warning at all and needs no Apple Developer account.
# (Verified: /opt/homebrew/bin/git and ffmpeg carry no quarantine attribute and open silently.)
#
# After the first PyPI release, refresh `url` and `sha256`:
#   shasum -a 256 dist/statementlens-<version>.tar.gz
class Statementlens < Formula
  include Language::Python::Virtualenv

  desc "Local-first personal-finance engine for bank and credit-card statements"
  homepage "https://github.com/udaysrinu/StatementLens"
  url "https://files.pythonhosted.org/packages/source/s/statementlens/statementlens-0.2.0.tar.gz"
  # digest of the 0.2.0 sdist built by packaging/release.sh; regenerate per release
  sha256 "1fe5fadd9edc4aaa252934362e5bff506456b7fd1c3b9028ba247197723501f3"
  license "MIT"

  depends_on "python@3.12"

  # pikepdf needs qpdf; installing it here means the user is not asked to fix a build error.
  depends_on "qpdf"

  def install
    virtualenv_install_with_resources
  end

  test do
    # a formula test must not touch the user's real store, so point at a scratch database
    output = shell_output("#{bin}/statementlens --db #{testpath}/t.db stats")
    assert_match "transactions", output
  end
end
