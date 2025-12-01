run_chatbot:
	@echo "Checking for processes running on port 8501..."
	@PID=$$(lsof -t -i:8501); \
	if [ -n "$$PID" ]; then \
		echo "Streamlit process found with PID: $$PID. Killing it..."; \
		kill -9 $$PID; \
		echo "Process killed successfully."; \
	else \
		echo "No process found running on port 8501."; \
	fi

	#@echo "Copying .env file into Evo-KG-Chatbot..."
	#@cp /home/pushpendrag/ankiss/evo_chatbot_env/.env Evo-KG-Chatbot/

	@echo "Launching Streamlit App..."
	@mkdir -p logs
	cd Evo-KG-Chatbot && make streamlit-dev
	#@systemctl restart nginx

