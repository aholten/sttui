class Stttui < Formula
  include Language::Python::Virtualenv

  desc "Speech-to-Text TUI — offline transcription powered by faster-whisper"
  homepage "https://github.com/aholten/sttui"
  url "https://files.pythonhosted.org/packages/source/s/stttui/stttui-0.2.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.12"
  depends_on "portaudio"

  # --- auto-generated resources ---
  # Resources will be populated by the update-homebrew workflow
  # after the first PyPI publish. Run `poet stttui` to generate manually.
  # --- end resources ---

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/stttui --version")
  end
end
