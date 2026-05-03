return {
  {
    "nvim-treesitter/nvim-treesitter",
    opts = {
      ensure_installed = {
        "bash",
        "css",
        "html",
        "javascript",
        "json",
        "jsonc",
        "lua",
        "luadoc",
        "markdown",
        "markdown_inline",
        "python",
        "query",
        "regex",
        "toml",
        "tsx",
        "typescript",
        "vim",
        "vimdoc",
        "yaml",
      },
    },
  },
  {
    "MeanderingProgrammer/render-markdown.nvim",
    ft = { "markdown", "Avante" },
    cmd = "RenderMarkdown",
    opts = {
      completions = { blink = { enabled = true } },
      file_types = { "markdown" },
      heading = { sign = false },
      code = {
        sign = false,
        width = "block",
        right_pad = 1,
      },
    },
  },
  {
    "ellisonleao/glow.nvim",
    cmd = "Glow",
    ft = { "markdown" },
    opts = {
      border = "rounded",
      style = "dark",
      width = 120,
    },
  },
  {
    "mikavilpas/yazi.nvim",
    event = "VeryLazy",
    dependencies = { "folke/snacks.nvim" },
    keys = {
      { "<leader>e", "<cmd>Yazi<cr>", desc = "Yazi file manager" },
      { "<leader>E", "<cmd>Yazi cwd<cr>", desc = "Yazi current directory" },
    },
    opts = {
      open_for_directories = true,
      keymaps = {
        show_help = "<f1>",
      },
    },
  },
}
