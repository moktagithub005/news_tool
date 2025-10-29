# Contributing to UNISOLE UPSC Notes System

Thank you for considering contributing to this project! Here are some guidelines to help you get started.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)
- Relevant logs or screenshots

### Suggesting Features

Feature requests are welcome! Please:
- Check if the feature has already been requested
- Provide clear use case and benefits
- Explain how it fits into the UPSC preparation workflow

### Code Contributions

1. **Fork the repository**

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**
   ```bash
   # Run tests (if available)
   pytest
   
   # Test with Docker
   docker compose build
   docker compose up -d
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: descriptive commit message"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Include screenshots for UI changes

## Code Style

- **Python**: Follow PEP 8 guidelines
- **Functions**: Use type hints where possible
- **Comments**: Write clear, concise comments
- **Naming**: Use descriptive variable and function names

## Project Areas for Contribution

### High Priority
- [ ] Improve PDF text extraction accuracy
- [ ] Add more news sources
- [ ] Enhance LLM integration
- [ ] Add unit tests
- [ ] Improve error handling

### Medium Priority
- [ ] Add user authentication
- [ ] Implement caching
- [ ] Add search functionality
- [ ] Mobile responsive UI
- [ ] Multi-language support (Hindi)

### Nice to Have
- [ ] Export to more formats (Markdown, JSON)
- [ ] Batch PDF processing
- [ ] Custom categorization rules
- [ ] Analytics dashboard
- [ ] Email notifications

## Development Setup

See [README.md](README.md) for detailed setup instructions.

## Questions?

Feel free to open an issue for any questions or clarifications.

Thank you for contributing! 🙏