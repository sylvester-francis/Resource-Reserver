if (!process.env.CSS_TRANSFORMER_WASM) {
  process.env.CSS_TRANSFORMER_WASM = '1';
}

const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
