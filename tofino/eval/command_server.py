from server import CommandServer

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('-p',
                        '--port', help="Ports where we listen to commands",
                        type=str, required=True)

    args = parser.parse_args()

    # start server
    s = CommandServer(int(args.port))
    s.run()
