# Argumentation
Argumentation is a Python library that bridges Pydantic models with argparse to create robust, type-safe command-line interfaces with minimal boilerplate. Define your application's configuration using Pydantic models, and Argumentation handles the command-line parsing, validation, and configuration file loading automatically.

## Features
- Type-safe Configuration: Utilize Pydantic's validation system for command-line arguments
- Configuration Files: Support for TOML, YAML, and JSON configuration files
- Automatic CLI Generation: Convert your Pydantic models into command-line interfaces automatically
- Rich Type Support: Handles complex types including:
    - Basic types (bool, int, float, str)
    - Lists and tuples
    - Literal types with choices
    - Union types
    - Custom Pydantic models

## Installation
1. uv (recommended)
```bash
uv add argumentation
```
2. poetry
```bash
poetry add argumentation
```
3. pip
```bash
pip install argumentation
```

## Usage

1. Create your configuration model using the ArgumentationModel
1. Create your main function which takes the configuration as an argument
1. Call the argumentation.run function with your main function

See `examples/simple.py` for more details

```bash
python examples/simple.py --name "My Application" --debug --port 5000 --hosts localhost 127.0.0.1
```

### Configuration Files

Argumentation supports loading configuration from TOML, YAML, and JSON files.
```bash
python examples/config.py --config examples/config.yaml
```

You can also override configuration file values from the command line.
```bash
python examples/simple.py --config examples/config.yaml --port 8888
```

## License

Argumentation is licensed under the MIT License. See the LICENSE file for details.