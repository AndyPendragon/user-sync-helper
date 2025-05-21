# User Sync Helper

This tool helps synchronize user accounts between different systems. It's designed to be flexible and extensible, allowing for various source and destination systems.

## Getting Started

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/AndyPendragon/user-sync-helper
cd user-sync-helper
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file by copying the example provided:

```bash
cp env.example .env
```

Edit the `.env` file to match your environment. This file contains configuration variables such as API keys or credentials

Make sure to keep this file **private**, as it may contain sensitive information.

### 3. Running the Script

Once the `.env` file is configured, run the main script:

```bash
python main.py
```

Refer to the `env.example` file for all supported keys and example values.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a new branch
3. Make your changes and test them
4. Submit a pull request

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
