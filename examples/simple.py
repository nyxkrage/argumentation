from argumentation import Argumentation, ArgumentationModel


class AppConfig(ArgumentationModel):
    name: str = "Default App"
    debug: bool = False
    port: int = 8080
    hosts: list[str] = []


def main(config: AppConfig):
    print(f"App name: {config.name}")
    print(f"Debug mode: {config.debug}")
    print(f"Port: {config.port}")
    print(f"Hosts: {config.hosts}")


if __name__ == "__main__":
    Argumentation.run(main)
