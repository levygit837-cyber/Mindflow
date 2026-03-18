import { AppRouter } from './router';
import { ThemeController } from './components/theme/ThemeController';
import './index.css';

function App() {
  return (
    <ThemeController>
      <AppRouter />
    </ThemeController>
  );
}

export default App;
