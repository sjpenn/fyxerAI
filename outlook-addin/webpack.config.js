const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';
  
  return {
    entry: {
      taskpane: './src/taskpane.js',
      commands: './src/commands.js'
    },
    
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: '[name].bundle.js',
      clean: true
    },
    
    resolve: {
      extensions: ['.js', '.html']
    },
    
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: ['@babel/preset-env']
            }
          }
        },
        {
          test: /\.css$/i,
          use: ['style-loader', 'css-loader']
        }
      ]
    },
    
    plugins: [
      new HtmlWebpackPlugin({
        template: './taskpane.html',
        filename: 'taskpane.html',
        chunks: ['taskpane']
      }),
      
      new HtmlWebpackPlugin({
        template: './commands.html',
        filename: 'commands.html',
        chunks: ['commands']
      }),
      
      new CopyWebpackPlugin({
        patterns: [
          {
            from: './manifest.xml',
            to: 'manifest.xml'
          },
          {
            from: '../static/icons',
            to: 'icons'
          }
        ]
      })
    ],
    
    devServer: {
      static: {
        directory: path.join(__dirname, 'dist')
      },
      compress: true,
      port: 3000,
      https: true,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'X-Requested-With, content-type, Authorization'
      },
      hot: true,
      liveReload: true
    },
    
    devtool: isProduction ? 'source-map' : 'eval-source-map'
  };
};