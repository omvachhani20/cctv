print("🤖 Chatbot Started!")
print("Type 'bye' to exit.\n")

while True:
    user_input = input("You: ").lower()

    if user_input == "hi" or user_input == "hello":
        print("Bot: Hello! Nice to meet you 😊")

    elif user_input == "how are you":
        print("Bot: I'm doing great! Thanks for asking.")

    elif user_input == "what is your name":
        print("Bot: My name is PythonBot.")

    elif user_input == "what can you do":
        print("Bot: I can chat with you and answer simple questions.")

    elif user_input == "bye":
        print("Bot: Goodbye! Have a nice day 👋")
        break

    else:
        print("Bot: Sorry, I didn't understand that.")

