local map = vim.keymap.set

map("n", "<leader>gg", function()
  Snacks.lazygit()
end, { desc = "Lazygit" })

map("n", "<leader>e", "<cmd>Yazi<cr>", { desc = "Yazi file manager" })
map("n", "<leader>E", "<cmd>Yazi cwd<cr>", { desc = "Yazi current directory" })
map("n", "<leader>md", "<cmd>RenderMarkdown toggle<cr>", { desc = "Toggle markdown render" })
map("n", "<leader>mg", "<cmd>Glow<cr>", { desc = "Preview markdown with Glow" })

map("n", "<leader>fp", function()
  Snacks.picker.files({ preview = "main" })
end, { desc = "Find files with preview" })

map("n", "<leader>sg", function()
  Snacks.picker.grep({ preview = "main" })
end, { desc = "Grep with preview" })
