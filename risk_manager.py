# risk_manager.py
import config

class RiskManager:
    def __init__(self):
        self.risk_per_trade = 0.02  # 0.01 (1% del balance total)
        self.max_bullets = 3  # Dividiremos la entrada en 3 "tiros" o promedios

    def calculate_position_size(self, account_balance, entry_price, stop_loss_price):
        """
        Calcula el tamaño TOTAL de la posición basada en el riesgo.
        """
        risk_amount = account_balance * self.risk_per_trade 
        risk_per_coin = abs(entry_price - stop_loss_price)
        
        if risk_per_coin == 0:
            return 0
            
        total_position_size = risk_amount / risk_per_coin
        
        # En lugar de comprar todo de golpe, calculamos el tamaño de 1 sola "bala"
        bullet_size = total_position_size / self.max_bullets
        return round(bullet_size, 4)

    def calculate_dynamic_stops(self, current_price, atr_value, action):
        """
        Utiliza el ATR (Volatilidad) para colocar el Stop Loss General y el Take Profit.
        """
        atr_multiplier = 2.00  # Damos más espacio para poder promediar sin que salte el SL
        
        if action == "LONG":
            stop_loss = current_price - (atr_value * atr_multiplier)
            take_profit = current_price + (atr_value * atr_multiplier * 2) 
        else: # SHORT
            stop_loss = current_price + (atr_value * atr_multiplier)
            take_profit = current_price - (atr_value * atr_multiplier * 2)
            
        return stop_loss, take_profit

    def calculate_averaging_levels(self, entry_price, atr_value, action):
        """
        La sugerencia del Trader: Calcula dónde poner las siguientes órdenes limit 
        para promediar el precio si el mercado va en nuestra contra.
        """
        # Usamos el 50% y el 100% de la volatilidad actual para añadir a la posición
        dca_levels = []
        
        if action == "LONG":
            # Si compramos y el precio cae, compramos más barato
            dca_levels.append(entry_price - (atr_value * 0.5))
            dca_levels.append(entry_price - (atr_value * 1.0))
        else:
            # Si vendemos y el precio sube (Ej: 75k a 78k), vendemos más caro
            dca_levels.append(entry_price + (atr_value * 0.5))
            dca_levels.append(entry_price + (atr_value * 1.0))
            
        return [float(round(level, 2)) for level in dca_levels]