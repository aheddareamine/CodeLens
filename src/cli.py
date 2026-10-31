class Cli:
    def index(self, max_chunk_size=2000):
        if max_chunk_size > 2000:
            print("Tooo long to go")
            return 
        print(max_chunk_size)
