import { AppBar, Toolbar, Typography, Box } from '@mui/material';

type HeaderProps = {
  configured: boolean;
};

export default function Header({ configured }: HeaderProps) {
  return (
    <AppBar position="static" sx={{ background: '#ffffff', borderBottom: '1px solid rgba(15, 23, 42, 0.08)', color: '#111827' }} elevation={0}>
      <Toolbar sx={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h6" sx={{ letterSpacing: 1, fontWeight: 700, color: '#111827' }}>
            FilmLens Control Center
          </Typography>
          <Typography variant="caption" sx={{ color: '#475569' }}>
            企业风格的电影分析智能体控制台
          </Typography>
        </Box>
        <Typography sx={{ color: configured ? '#16a34a' : '#f97316', fontWeight: 600 }}>
          {configured ? '已配置' : '未配置'}
        </Typography>
      </Toolbar>
    </AppBar>
  );
}
