import React, { useState } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/AppNavigator';
import { ArrowLeft, CreditCard, Wallet, Circle, CheckCircle2 } from 'lucide-react-native';
import apiClient from '../api/client';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'SelectMethod'>;
  route: RouteProp<RootStackParamList, 'SelectMethod'>;
};

export default function SelectMethodScreen({ navigation, route }: Props) {
  const insets = useSafeAreaInsets();
  const { sessionData } = route.params;
  const [selectedMethod, setSelectedMethod] = useState<string>('Credit Card');
  const [loading, setLoading] = useState(false);

  const paymentMethods = [
    { id: 'Credit Card', label: 'Credit Card', icon: CreditCard },
    { id: 'Touch n Go', label: "Touch 'n Go", icon: Wallet },
  ];

  const handleConfirmPay = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post(`/parking-sessions/${sessionData.id}/pay`, {
        payment_method: selectedMethod,
      });
      
      const { receipt } = response.data;
      navigation.navigate('Receipt', {
        receiptData: receipt,
        sessionData: sessionData,
      });
    } catch (error) {
      Alert.alert('Payment Failed', 'An error occurred while processing your payment.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="flex-1 bg-white" style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}>
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 py-3 border-b border-gray-100">
        <View className="flex-row items-center">
          <TouchableOpacity className="p-2" onPress={() => navigation.goBack()}>
            <ArrowLeft size={24} color="#333" />
          </TouchableOpacity>
          <Text className="font-interBold text-lg ml-2 text-gray-800">Select Method</Text>
        </View>
        <View className="bg-blue-50 px-3 py-1 rounded-full">
          <Text className="font-interBold text-[#007BFF]">Total: ${Number(sessionData.amount_due).toFixed(2)}</Text>
        </View>
      </View>

      <View className="flex-1 px-6 pt-6">
        <Text className="font-inter text-gray-500 mb-4">Choose your payment option</Text>

        {paymentMethods.map((method) => {
          const IconComponent = method.icon;
          const isSelected = selectedMethod === method.id;

          return (
            <TouchableOpacity
              key={method.id}
              activeOpacity={0.8}
              onPress={() => setSelectedMethod(method.id)}
              className={`flex-row items-center p-4 mb-4 rounded-xl border ${
                isSelected ? 'border-[#007BFF] bg-[#F0F7FF]' : 'border-gray-200 bg-white'
              }`}
            >
              <View className={`w-10 h-10 rounded-full items-center justify-center ${isSelected ? 'bg-[#007BFF]/10' : 'bg-gray-100'}`}>
                <IconComponent size={20} color={isSelected ? '#007BFF' : '#666'} />
              </View>
              <Text className={`flex-1 ml-4 font-interBold text-[16px] ${isSelected ? 'text-[#007BFF]' : 'text-gray-800'}`}>
                {method.label}
              </Text>
              {isSelected ? (
                <CheckCircle2 size={24} color="#007BFF" />
              ) : (
                <Circle size={24} color="#ccc" />
              )}
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Footer Action */}
      <View className="px-6 py-4 bg-white border-t border-gray-100">
        <TouchableOpacity
          className="w-full h-[56px] bg-[#007BFF] rounded-lg items-center justify-center"
          style={{
            shadowColor: '#007BFF',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.2,
            shadowRadius: 8,
            elevation: 4,
          }}
          onPress={handleConfirmPay}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="font-interBold text-white text-[16px]">Confirm Pay</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}
